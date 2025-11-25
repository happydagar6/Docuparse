from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class ChatMessage(BaseModel):
    id: Optional[str] = None
    session_id: str
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    
class ChatSession(BaseModel):
    id: Optional[str] = None
    paper_id: str
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    
class ChatResponse(BaseModel):
    session_id: str # The chat session ID
    message: ChatMessage # The assistant's reply
    sources: List[Dict[str, Any]] = Field(default_factory=list) # List of source references

class StreamingChatChunk(BaseModel):
    type: str = Field(..., pattern="^(token|sources|complete|error)$")
    content: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    error: Optional[str] = None