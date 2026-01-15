# models/__init__.py

# Import paper models
from .paper import (
    PaperUpload, 
    PaperSummary,
    SearchFilters,
    SearchQuery, 
    ProcessingRequest, 
    ProcessingResponse,
    Theme,
    TimelinePoint,
    TrendsAnalysis,
    TopPaper,
)

# Import chat models
from .chat import ChatMessage, ChatSession, ChatRequest, ChatResponse, StreamingChatChunk

# Import export models
from .export import APAExportRequest, ParagraphContent, ReferenceMetadata

# Import note models
from .note import NoteBase, NoteCreate, NoteUpdate, NoteResponse, NoteListResponse

# Export all models
__all__ = [
    'PaperUpload', 
    'PaperSummary',
    'SearchFilters',
    'SearchQuery', 
    'ProcessingRequest', 
    'ProcessingResponse',
    'Theme',
    'TimelinePoint',
    'TrendsAnalysis',
    'TopPaper',
    'ChatMessage',
    'ChatSession', 
    'ChatRequest', 
    'ChatResponse',
    'StreamingChatChunk',
    'APAExportRequest',
    'ParagraphContent',
    'ReferenceMetadata',
    'NoteBase',
    'NoteCreate',
    'NoteUpdate',
    'NoteResponse',
    'NoteListResponse'
]