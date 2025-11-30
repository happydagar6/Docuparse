# models/__init__.py

# Import paper models
from .paper import (
    PaperUpload, 
    PaperSummary, 
    SearchQuery, 
    ProcessingRequest, 
    ProcessingResponse,
    Theme,
    TimelinePoint,
    TrendsAnalysis,
    TopPaper,
    SynthesisRequest,
    SynthesisResponse,
    SynthesisHistoryItem,
    SynthesisHistoryListItem,
    SaveSynthesisRequest,
    UpdateSynthesisTagsRequest
)

# Import chat models
from .chat import ChatMessage, ChatSession, ChatRequest, ChatResponse, StreamingChatChunk

# Export all models
__all__ = [
    'PaperUpload', 
    'PaperSummary', 
    'SearchQuery', 
    'ProcessingRequest', 
    'ProcessingResponse',
    'Theme',
    'TimelinePoint',
    'TrendsAnalysis',
    'TopPaper',
    'SynthesisRequest',
    'SynthesisResponse',
    'SynthesisHistoryItem',
    'SynthesisHistoryListItem',
    'SaveSynthesisRequest',
    'UpdateSynthesisTagsRequest',
    'ChatMessage',
    'ChatSession', 
    'ChatRequest', 
    'ChatResponse',
    'StreamingChatChunk'
]