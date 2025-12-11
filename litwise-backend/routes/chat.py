from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
import asyncio
from datetime import datetime
import uuid

from models.chat import ChatSession, ChatRequest, ChatMessage, ChatResponse
from chat_pipeline import rag_pipeline
from workflow.db import supabase
from auth_middleware import get_current_user, AuthUser

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
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase_client.table("chat_sessions").insert(session_data).execute()
        
        return ChatSession(**result.data[0])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

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
        
        # Verify session exists and user owns the paper
        session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        paper_check = supabase_client.table("papers").select("id").eq("id", session_result.data[0]["paper_id"]).eq("user_id", current_user.id).execute()
        if not paper_check.data:
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
async def stream_chat(request: ChatRequest, current_user: AuthUser = Depends(get_current_user)):
    """Stream chat response with real-time updates. User must own the associated paper."""
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
            "created_at": datetime.now().isoformat()
        }
        
        supabase_client.table("chat_messages").insert(user_message_data).execute()
        
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
                            "created_at": datetime.now().isoformat()
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
                    "created_at": datetime.now().isoformat()
                }
                
                supabase_client.table("chat_messages").insert(assistant_message_data).execute()
                
                # Update session timestamp
                supabase_client.table("chat_sessions").update({
                    "updated_at": datetime.now().isoformat()
                }).eq("id", session_id).execute()
                
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
        
        # Verify session exists and user owns the paper
        session_result = supabase_client.table("chat_sessions").select("paper_id").eq("id", session_id).execute()
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        paper_check = supabase_client.table("papers").select("id").eq("id", session_result.data[0]["paper_id"]).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # Delete session (cascades to messages and memory)
        result = supabase_client.table("chat_sessions").delete().eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"message": "Chat session deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")