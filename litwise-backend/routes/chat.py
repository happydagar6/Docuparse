from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
from datetime import datetime, timezone
import uuid
import base64

from models.chat import ChatSession, ChatRequest, ChatMessage, PaginatedMessages
from chat_pipeline import rag_pipeline
from workflow.db import supabase
from auth_middleware import get_current_user, AuthUser

from services.rate_limiter_service import rate_limit_dependency
from services.message_cache_service import (
    cache_get, 
    cache_set, 
    cache_invalidate,
    get_cached_session_paper,
    cache_session_paper,
    get_cached_paper_ownership,
    cache_paper_ownership
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(paper_id: str, current_user: AuthUser = Depends(get_current_user), title: Optional[str] = None):
    """Create a new chat session for a paper. User must own the paper."""
    try:
        supabase_client = supabase
        
        # Verify paper exists and user owns it
        paper_result = supabase_client.table("papers").select("id, title").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_result.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        paper_title = paper_result.data[0]["title"]
        session_title = title or f"Chat with {paper_title}"
        
        # Create session
        session_data = {
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "title": session_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.table("chat_sessions").insert(session_data).execute()
        
        return ChatSession(**result.data[0])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")




@router.get("/sessions/{session_id}/messages/paginated")
async def get_paginated_chat_messages(
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    direction: str = Query("before"),
    current_user: AuthUser = Depends(get_current_user)
): 
    """
    Get paginated messages for a chat session using cursor-based pagination.
    
    Features:
    - Redis L2 cache: Caches results for 24 hours to reduce DB queries
    - Cursor-based pagination: Bi-directional scrolling (before/after)
    - Database indexing: O(log n) query performance with proper indexes
    - Graceful degradation: Falls back to DB if Redis unavailable
    
    Args:
        session_id: Chat session ID
        limit: Messages per page (1-100)
        cursor: Pagination cursor (base64 encoded)
        direction: "before" for older messages, "after" for newer
        
    Returns:
        PaginatedMessages with messages list and next cursor
    """
    try:
        supabase_client = supabase
        
        # STEP 1: Check cached session-to-paper mapping
        paper_id = get_cached_session_paper(session_id)
        
        if paper_id is None:
            # Cache miss - query database for session
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            if not session_result.data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            paper_id = session_result.data[0]["paper_id"]
            # Cache the session-to-paper mapping (15 min TTL)
            cache_session_paper(session_id, paper_id)
        
        # STEP 2: Check cached paper ownership
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        
        if owns_paper is None:
            # Cache miss - query database for ownership
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            owns_paper = bool(paper_check.data)
            # Cache the ownership status (15 min TTL)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # CHECK REDIS CACHE FIRST (L2 Cache)
        cached_result = cache_get(session_id, limit, cursor, direction)
        if cached_result:
            # Cache hit - return immediately
            return PaginatedMessages(
                messages=[ChatMessage(**msg) for msg in cached_result["messages"]],
                has_more=cached_result["has_more"],
                next_cursor=cached_result["next_cursor"],
                total_count=cached_result["total_count"]
            )
        
        # CACHE MISS - Query database
        query = supabase_client.table("chat_messages").select("*", count="exact").eq("session_id", session_id)
        
        # Decode and apply cursor filtering if provided
        if cursor:
            try:
                decoded = base64.b64decode(cursor).decode()
                cursor_data = json.loads(decoded)
                cursor_timestamp = datetime.fromisoformat(cursor_data["timestamp"])
                
                if direction == "before":
                    # Load messages BEFORE the cursor (older messages)
                    query = query.lt("created_at", cursor_timestamp.isoformat())
                elif direction == "after":
                    # Load messages AFTER the cursor (newer messages)
                    query = query.gt("created_at", cursor_timestamp.isoformat())
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid cursor format")
        
        # Execute query with ordering and limit
        result = query.order("created_at", desc=True).limit(limit + 1).execute()
        
        messages_data = result.data
        total_count = result.count
        
        # Check if there are more messages
        has_more = len(messages_data) > limit
        if has_more:
            messages_data = messages_data[:limit]
        
        # Convert to ChatMessage objects
        messages = [
            ChatMessage(
                id=msg_data.get("id"),
                session_id=msg_data.get("session_id"),
                role=msg_data.get("role"),
                content=msg_data.get("content"),
                sources=msg_data.get("sources", []),
                created_at=msg_data.get("created_at")
            )
            for msg_data in messages_data
        ]
        
        # Generate next cursor from last message
        next_cursor = None
        if has_more and messages:
            last_message = messages[-1]
            cursor_payload = {
                'timestamp': last_message.created_at.isoformat() if last_message.created_at else datetime.utcnow().isoformat(),
                'id': last_message.id
            }
            next_cursor = base64.b64encode(json.dumps(cursor_payload).encode()).decode()
        
        # STORE IN REDIS CACHE for next request (L2 Cache)
        messages_dict = [msg.dict() for msg in messages]
        cache_set(
            session_id=session_id,
            limit=limit,
            messages=messages_dict,
            next_cursor=next_cursor,
            total_count=total_count,
            has_more=has_more,
            cursor=cursor,
            direction=direction
        )
        
        return PaginatedMessages(
            messages=messages,
            has_more=has_more,
            next_cursor=next_cursor,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch paginated messages: {str(e)}")



@router.get("/sessions/{session_id}/messages/count")
async def get_message_count(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """Get total message count for a session - lightweight query"""
    try:
        supabase_client = supabase
        
        # Check cached session-to-paper mapping
        paper_id = get_cached_session_paper(session_id)
        
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            if not session_result.data:
                raise HTTPException(status_code=404, detail="Not found")
            paper_id = session_result.data[0]["paper_id"]
            cache_session_paper(session_id, paper_id)
        
        # Check cached paper ownership
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            owns_paper = bool(paper_check.data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Access denied")
        
        # Count-only query (very fast with index)
        result = supabase_client.table("chat_messages").select(
            "id", count="exact"
        ).eq("session_id", session_id).execute()
        
        return {"count": result.count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{paper_id}", response_model=List[ChatSession])
async def get_paper_chat_sessions(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get all chat sessions for a paper. User must own the paper."""
    try:
        supabase_client = supabase
        
        # Verify paper ownership
        paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        result = supabase_client.table("chat_sessions").select("*").eq(
            "paper_id", paper_id
        ).order("updated_at", desc=True).execute()
        
        return [ChatSession(**session) for session in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat sessions: {str(e)}")

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get all messages in a chat session. User must own the associated paper."""
    try:
        supabase_client = supabase
        
        # Check cached session-to-paper mapping
        paper_id = get_cached_session_paper(session_id)
        
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            if not session_result.data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            paper_id = session_result.data[0]["paper_id"]
            cache_session_paper(session_id, paper_id)
        
        # Check cached paper ownership
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            owns_paper = bool(paper_check.data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        result = supabase_client.table("chat_messages").select("*").eq(
            "session_id", session_id
        ).order("created_at").execute()
        
        print(f"Raw messages data: {result.data}")
        
        # Validate and convert messages
        messages = []
        for message_data in result.data:
            try:
                # Ensure all required fields are present
                validated_message = {
                    "id": message_data.get("id"),
                    "session_id": message_data.get("session_id"),
                    "role": message_data.get("role"),
                    "content": message_data.get("content"),
                    "sources": message_data.get("sources", []),
                    "created_at": message_data.get("created_at")
                }
                messages.append(ChatMessage(**validated_message))
            except Exception as validation_error:
                print(f"Message validation error: {validation_error}")
                print(f"Problematic message data: {message_data}")
                continue
                
        return messages
        
    except Exception as e:
        print(f"Chat messages error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat messages: {str(e)}")

@router.post("/stream")
async def stream_chat(
    request: ChatRequest, 
    current_user: AuthUser = Depends(get_current_user),
    rate_limit_check = Depends(rate_limit_dependency)):
    """Stream chat response with real-time updates. User must own the associated paper."""
    
    # Rate limit already checked by middleware, but we have info available
    if not rate_limit_check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {rate_limit_check['remaining']}"
        )
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        print(f"Starting chat stream for session: {session_id}, message: {request.message}")
        
        # Get session details and verify ownership
        supabase_client = supabase
        session_result = supabase_client.table("chat_sessions").select("*").eq(
            "id", session_id
        ).execute()
        
        
        # Verify session exists
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = session_result.data[0]
        paper_id = session["paper_id"]
        
        # Verify paper ownership
        paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # Save user message
        user_message_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": request.message,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase_client.table("chat_messages").insert(user_message_data).execute()
        
        # INVALIDATE REDIS CACHE - New user message added
        cache_invalidate(session_id)
        
        async def generate_stream():
            try:
                print(f"Starting stream generation for session: {session_id}")
                
                assistant_message_id = str(uuid.uuid4())
                full_response = ""
                sources = []
                
                async for chunk in rag_pipeline.chat_stream(
                    question=request.message,
                    session_id=session_id,
                    paper_id=paper_id
                ):
                    # Chunk is already a dict from the updated pipeline
                    # Send chunk to client
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    if chunk.get("type") == "token" and chunk.get("content"):
                        full_response += chunk["content"]
                    elif chunk.get("type") == "sources" and chunk.get("sources"):
                        sources = chunk["sources"]
                    elif chunk.get("type") == "error":
                        # Save error message
                        error_message_data = {
                            "id": assistant_message_id,
                            "session_id": session_id,
                            "role": "assistant",
                            "content": f"Error: {chunk.get('error')}",
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        supabase_client.table("chat_messages").insert(error_message_data).execute()
                        return
                
                # Save assistant response
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
                
                # INVALIDATE REDIS CACHE - New message added
                cache_invalidate(session_id)
                
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "error": f"Stream generation failed: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

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

@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete a chat session and all its messages. User must own the associated paper."""
    try:
        supabase_client = supabase
        
        # Check cached session-to-paper mapping
        paper_id = get_cached_session_paper(session_id)
        
        if paper_id is None:
            session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
            if not session_result.data:
                raise HTTPException(status_code=404, detail="Chat session not found")
            paper_id = session_result.data[0]["paper_id"]
            cache_session_paper(session_id, paper_id)
        
        # Check cached paper ownership
        owns_paper = get_cached_paper_ownership(paper_id, current_user.id)
        
        if owns_paper is None:
            paper_check = supabase_client.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            owns_paper = bool(paper_check.data)
            cache_paper_ownership(paper_id, current_user.id, owns_paper)
        
        if not owns_paper:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # Delete session (cascades to messages and memory)
        result = supabase_client.table("chat_sessions").delete().eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"message": "Chat session deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")