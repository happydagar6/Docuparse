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
    SynthesisRequest,
    SynthesisResponse,
    SynthesisHistoryItem,
    SynthesisHistoryListItem,
    SaveSynthesisRequest,
    UpdateSynthesisTagsRequest
)

# Import chat models
from .chat import ChatMessage, ChatSession, ChatRequest, ChatResponse, StreamingChatChunk

# Import export models
from .export import APAExportRequest, ParagraphContent, ReferenceMetadata

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
    'StreamingChatChunk',
    'APAExportRequest',
    'ParagraphContent',
    'ReferenceMetadata'
]