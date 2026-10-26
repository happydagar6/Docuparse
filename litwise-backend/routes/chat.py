"""
=============================================================================
FastAPI Chat Router (`routes/chat.py`)
=============================================================================
This file defines all API endpoints for the Chat module, including:
1. Creating a new chat session for a paper.
2. Fetching paginated chat history (with Redis L2 caching and cursor pagination).
3. Getting message counts.
4. Fetching all sessions / messages for a given paper.
5. Real-time streaming AI response generation (Server-Sent Events / SSE).
6. Deleting a chat session.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, cast, Any
import json
from datetime import datetime, timezone
import uuid
import base64

# Pydantic models for request/response validation
from models.chat import ChatSession, ChatRequest, ChatMessage, PaginatedMessages, CreateChatSessionRequest
# RAG Chat Pipeline instance
from services.rag.generator import rag_generator
# Supabase database client instance
from workflow.db import supabase
# Authentication middleware for JWT verification & route protection
from middleware import get_current_user, AuthUser

# Rate limiting service dependency
from services.rate_limiter_service import rate_limit_dependency
# Redis L2 cache helper functions for session metadata and paginated message caching
from services.message_cache_service import (
    cache_get, 
    cache_set, 
    cache_invalidate,
    get_cached_session_paper,
    cache_session_paper,
    get_cached_paper_ownership,
    cache_paper_ownership
)

# Create FastAPI router with a common URL prefix `/api/chat`
router = APIRouter(prefix="/api/chat", tags=["chat"])


# =============================================================================
# ENDPOINT 1: Create a New Chat Session
# =============================================================================
@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    paper_id: str, 
    request: CreateChatSessionRequest,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Creates a new chat session associated with a specific PDF/paper.
    
    Security:
    - User must be authenticated (`get_current_user`).
    - Verifies that the paper exists AND belongs to the authenticated user.
    """
    try:
        supabase_client = supabase
        
        # Step 1: Security Check - Ensure the paper exists and belongs to current_user
        paper_result = supabase_client.table("papers").select("id, title").eq("id", paper_id).eq("user_id", current_user.id).execute()
        paper_data = cast(List[Any], paper_result.data or [])
        if not paper_data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        paper_title = paper_data[0]["title"]
        session_title = request.title or f"Chat with {paper_title}"
        
        # Step 2: Prepare new chat session payload
        session_data = {
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "title": session_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Step 3: Insert into Supabase 'chat_sessions' table
        result = supabase_client.table("chat_sessions").insert(session_data).execute()
        
        # Return validated Pydantic model
        res_data = cast(List[Any], result.data or [])
        return ChatSession(**res_data[0])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")


# =============================================================================
# ENDPOINT 2: Paginated Chat Messages (Infinite Scroll Support + Redis L2 Cache)
# =============================================================================
@router.get("/sessions/{session_id}/messages/paginated")
async def get_paginated_chat_messages(
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    direction: str = Query("before"),
    current_user: AuthUser = Depends(get_current_user)
): 
    """
    Fetches a paginated slice of chat messages using cursor-based pagination.
    
    Architecture Highlights:
    1. Redis Cache First: Checks L2 Redis cache before querying PostgreSQL.
    2. Session & Ownership Caching: Uses Redis to cache session-to-paper mapping
       and paper ownership checks (15 min TTL) to minimize DB joins.
    3. Bi-directional Cursor Pagination: Base64 encoded cursor filtering (`lt` or `gt` on created_at).
    """
    try:
        supabase_client = supabase
        
        # =====================================================================
        # [LITWISE ARCHITECTURE]: CACHE-ASIDE PATTERN (Step-by-Step)
        # Why it's called "Cache-Aside": The application code sits between the cache
        # and the database. The app checks Redis "on the side":
        # 1. Look in Cache first.
        # 2. If HIT -> Return immediately (sub-5ms response).
        # 3. If MISS -> Read from PostgreSQL database, populate Cache, then return.
        # 4. On write/insert -> Invalidate (delete) cache so stale data is never served.
        # =====================================================================
        
        # ---------------------------------------------------------------------
        # STEP 1: Verify Session & Paper Ownership (Cached in Redis - 15m TTL)
        # Why we cache this: Avoids 2 expensive SQL JOIN/SELECT queries on every scroll.
        # ---------------------------------------------------------------------
        paper_id = get_cached_session_paper(session_id)
        if paper_id is None:
            # Cache Miss: Query Supabase for session -> paper mapping
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            s_data = cast(List[Any], session_result.data or [])
            if not s_data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            paper_id = cast(str, s_data[0]["paper_id"])
            cache_session_paper(session_id, paper_id) # Save in Redis cache (15m TTL)
        
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        if owns_paper is None:
            # Cache Miss: Verify if current_user owns this paper
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            p_data = cast(List[Any], paper_check.data or [])
            owns_paper = bool(p_data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper) # Save ownership in Redis
        
        if not owns_paper:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # ---------------------------------------------------------------------
        # STEP 2: Cache-Aside Read: Check Redis for Paginated Messages (L2 Cache)
        # Key format: `messages:{session_id}:{limit}:{direction}:{cursor}`
        # ---------------------------------------------------------------------
        cached_result = cache_get(session_id, limit, cursor, direction)
        if cached_result:
            # ⚡ CACHE HIT: Return data immediately without touching PostgreSQL!
            return PaginatedMessages(
                messages=[ChatMessage(**msg) for msg in cached_result["messages"]],
                has_more=cached_result["has_more"],
                next_cursor=cached_result["next_cursor"],
                total_count=cached_result["total_count"]
            )
        
        # ---------------------------------------------------------------------
        # STEP 3: CACHE MISS -> Query PostgreSQL Database (Supabase)
        # If not in Redis, we run the real SQL query on the database.
        # ---------------------------------------------------------------------
        query = supabase_client.table("chat_messages").select("*", count=cast(Any, "exact")).eq("session_id", session_id)
        
        # Decode base64 cursor timestamp if provided for pagination
        if cursor:
            try:
                decoded = base64.b64decode(cursor).decode()
                cursor_data = json.loads(decoded)
                cursor_timestamp = datetime.fromisoformat(cursor_data["timestamp"])
                
                if direction == "before":
                    # Load messages created BEFORE cursor (older messages)
                    query = query.lt("created_at", cursor_timestamp.isoformat())
                elif direction == "after":
                    # Load messages created AFTER cursor (newer messages)
                    query = query.gt("created_at", cursor_timestamp.isoformat())
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid cursor format")
        
        # Execute query (fetch limit + 1 items to determine if `has_more` exists)
        result = query.order("created_at", desc=True).limit(limit + 1).execute()
        
        messages_data = cast(List[Any], result.data or [])
        total_count = cast(Optional[int], result.count)
        
        # Determine if additional pages exist
        has_more = len(messages_data) > limit
        if has_more:
            messages_data = messages_data[:limit]
        
        # Map raw DB records to Pydantic ChatMessage models
        messages = [
            ChatMessage(
                id=str(msg_data.get("id", "")),
                session_id=str(msg_data.get("session_id") or session_id),
                role=str(msg_data.get("role", "user")),
                content=str(msg_data.get("content", "")),
                sources=msg_data.get("sources", []),
                created_at=msg_data.get("created_at")
            )
            for msg_data in messages_data
            if isinstance(msg_data, dict)
        ]
        
        # Encode next cursor (timestamp + ID) into Base64 for the frontend
        next_cursor = None
        if has_more and messages:
            last_message = messages[-1]
            cursor_payload = {
                'timestamp': last_message.created_at.isoformat() if last_message.created_at else datetime.now(timezone.utc).isoformat(),
                'id': last_message.id
            }
            next_cursor = base64.b64encode(json.dumps(cursor_payload).encode()).decode()
        
        # ---------------------------------------------------------------------
        # STEP 4: Cache-Aside Write: Save Query Result into Redis L2 Cache
        # Why we do this: The next time the user or frontend requests this exact page,
        # it will HIT Redis and skip PostgreSQL completely (24-hour TTL).
        # ---------------------------------------------------------------------
        messages_dict = [msg.model_dump() for msg in messages]
        cache_set(
            session_id=session_id,
            limit=limit,
            messages=messages_dict,
            next_cursor=next_cursor,
            total_count=total_count or 0,
            has_more=has_more,
            cursor=cursor,
            direction=direction
        )
        
        return PaginatedMessages(
            messages=messages,
            has_more=has_more,
            next_cursor=next_cursor,
            total_count=total_count or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch paginated messages: {str(e)}")


# =============================================================================
# ENDPOINT 3: Get Message Count
# =============================================================================
@router.get("/sessions/{session_id}/messages/count")
async def get_message_count(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """Returns total message count for a session using a lightweight count-only query."""
    try:
        supabase_client = supabase
        
        paper_id = get_cached_session_paper(session_id)
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            s_data = cast(List[Any], session_result.data or [])
            if not s_data:
                raise HTTPException(status_code=404, detail="Not found")
            paper_id = cast(str, s_data[0]["paper_id"])
            cache_session_paper(session_id, paper_id)
        
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            p_data = cast(List[Any], paper_check.data or [])
            owns_paper = bool(p_data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Access denied")
        
        # Fast SQL count using DB index
        result = supabase_client.table("chat_messages").select(
            "id", count=cast(Any, "exact")
        ).eq("session_id", session_id).execute()
        
        return {"count": result.count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT 4: Get All Chat Sessions for a Paper
# =============================================================================
@router.get("/sessions/{paper_id}", response_model=List[ChatSession])
async def get_paper_chat_sessions(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Fetches all chat sessions linked to a specific paper."""
    try:
        supabase_client = supabase
        
        # Security Check: User must own the paper
        paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        result = supabase_client.table("chat_sessions").select("*").eq(
            "paper_id", paper_id
        ).order("updated_at", desc=True).execute()
        
        sessions_data = cast(List[Any], result.data or [])
        return [ChatSession(**session) for session in sessions_data if isinstance(session, dict)]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat sessions: {str(e)}")


# =============================================================================
# ENDPOINT 5: Get All Messages for a Chat Session
# =============================================================================
@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Fetches all messages for a session (chronologically sorted)."""
    try:
        supabase_client = supabase
        
        # Cached ownership checks
        paper_id = get_cached_session_paper(session_id)
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            s_data = cast(List[Any], session_result.data or [])
            if not s_data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            paper_id = cast(str, s_data[0]["paper_id"])
            cache_session_paper(session_id, paper_id)
        
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            p_data = cast(List[Any], paper_check.data or [])
            owns_paper = bool(p_data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        result = supabase_client.table("chat_messages").select("*").eq(
            "session_id", session_id
        ).order("created_at").execute()
        
        messages = []
        msg_list = cast(List[Any], result.data or [])
        for message_data in msg_list:
            if isinstance(message_data, dict):
                try:
                    validated_message = {
                        "id": str(message_data.get("id", "")),
                        "session_id": str(message_data.get("session_id") or session_id),
                        "role": str(message_data.get("role", "user")),
                        "content": str(message_data.get("content", "")),
                        "sources": message_data.get("sources", []),
                        "created_at": message_data.get("created_at")
                    }
                    messages.append(ChatMessage(**validated_message))
                except Exception as validation_error:
                    print(f"Message validation error: {validation_error}")
                    continue
                
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat messages: {str(e)}")


# =============================================================================
# ENDPOINT 6: REAL-TIME CHAT STREAMING (Server-Sent Events / SSE)
# =============================================================================
@router.post("/stream")
async def stream_chat(
    request: ChatRequest, 
    current_user: AuthUser = Depends(get_current_user),
    rate_limit_check = Depends(rate_limit_dependency)):
    """
    Streams AI responses token-by-token using Server-Sent Events (SSE).
    
    Workflow:
    1. Checks Rate Limit dependency (throttles spam).
    2. Validates session existence & paper ownership.
    3. Saves the User's question into Supabase database.
    4. Invalidates Redis cache for this session (since new message was added).
    5. Runs an Async Generator (`generate_stream`) to fetch tokens live from `rag_pipeline.chat_stream`.
    6. Yields SSE chunks (`data: <json>\n\n`) to the frontend HTTP stream in real time.
    7. After streaming completes, saves full AI assistant response to Supabase.
    """
    
    # -------------------------------------------------------------------------
    # STEP 1: Rate Limiting Check
    # -------------------------------------------------------------------------
    if not rate_limit_check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {rate_limit_check['remaining']}"
        )
        
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        supabase_client = supabase
        
        # ---------------------------------------------------------------------
        # STEP 2: Verify Session & Paper Ownership
        # ---------------------------------------------------------------------
        session_result = supabase_client.table("chat_sessions").select("*").eq("id", session_id).execute()
        s_data = cast(List[Any], session_result.data or [])
        if not s_data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = s_data[0]
        paper_id = cast(str, session["paper_id"])
        
        paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        p_data = cast(List[Any], paper_check.data or [])
        if not p_data:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # ---------------------------------------------------------------------
        # STEP 3: Save User Message in Supabase DB
        # ---------------------------------------------------------------------
        user_message_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": request.message,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase_client.table("chat_messages").insert(user_message_data).execute()
        
        # [LITWISE CACHE-ASIDE PATTERN]: Invalidate on Write
        # Why we do this: In Cache-Aside, when new data is written to the DB, the cache
        # must be purged so future read queries don't return stale/outdated message lists.
        cache_invalidate(session_id)
        
        # ---------------------------------------------------------------------
        # STEP 4: Async Stream Generator Function
        # ---------------------------------------------------------------------
        async def generate_stream():
            try:
                assistant_message_id = str(uuid.uuid4())
                full_response = ""
                sources = []
                
                # Consume live tokens from RAG pipeline generator
                async for chunk in rag_generator.chat_stream(
                    question=request.message,
                    session_id=session_id,
                    paper_id=paper_id
                ):
                    # Format as SSE string: 'data: <json>\n\n'
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    if chunk.get("type") == "token" and chunk.get("content"):
                        full_response += chunk["content"]
                    elif chunk.get("type") == "sources" and chunk.get("sources"):
                        sources = chunk["sources"]
                    elif chunk.get("type") == "error":
                        error_message_data = {
                            "id": assistant_message_id,
                            "session_id": session_id,
                            "role": "assistant",
                            "content": f"Error: {chunk.get('error')}",
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        supabase_client.table("chat_messages").insert(error_message_data).execute()
                        return
                
                # -------------------------------------------------------------
                # STEP 5: Save Completed AI Assistant Message to DB
                # -------------------------------------------------------------
                assistant_message_data = {
                    "id": assistant_message_id,
                    "session_id": session_id,
                    "role": "assistant",
                    "content": full_response,
                    "sources": sources,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                supabase_client.table("chat_messages").insert(assistant_message_data).execute()
                
                # Update session timestamp
                supabase_client.table("chat_sessions").update({
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", session_id).execute()
                
                # Invalidate Redis cache again to include the completed assistant message
                cache_invalidate(session_id)
                
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "error": f"Stream generation failed: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

        # Return FastAPI StreamingResponse headers for SSE
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream chat: {str(e)}")


# =============================================================================
# ENDPOINT 7: Delete Chat Session
# =============================================================================
@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Deletes a chat session and all associated messages."""
    try:
        supabase_client = supabase
        
        # Ownership check
        paper_id = get_cached_session_paper(session_id)
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            s_data = cast(List[Any], session_result.data or [])
            if not s_data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            paper_id = cast(str, s_data[0]["paper_id"])
            cache_session_paper(session_id, paper_id)
        
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            p_data = cast(List[Any], paper_check.data or [])
            owns_paper = bool(p_data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # Delete session record (Supabase foreign key CASCADE deletes linked messages)
        result = supabase_client.table("chat_sessions").delete().eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Invalidate Redis cache
        cache_invalidate(session_id)
        
        return {"message": "Chat session deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")