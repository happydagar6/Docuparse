# models/__init__.py

# Import paper models
from .paper import (
    AuthorInfo,
    PaperMetadata,
    PaperUpload, 
    PaperSummary,
    SearchFilters,
    SearchQuery, 
    ParsedQueryInfo,
    ProcessingRequest, 
    ProcessingResponse,
    Theme,
    TimelinePoint,
    TrendsAnalysis,
    TopPaper,
    ImageContent,
    TableContent,
    MultiModalContent,
    ChunkType,
    MultiModalChunk,
)

# Import chat models
from .chat import ChatMessage, ChatSession, ChatRequest, ChatResponse, StreamingChatChunk

# Import export models
from .export import APAExportRequest, ParagraphContent, ReferenceMetadata

# Import note models
from .note import NoteBase, NoteCreate, NoteUpdate, NoteResponse, NoteListResponse

# Import quiz models
from .quiz import (
    DifficultyLevel,
    QuizType,
    QuizOption,
    QuizQuestion,
    QuizConfig,
    QuizResponse,
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizListResponse,
)

# Export all models
__all__ = [
    'AuthorInfo',
    'PaperMetadata',
    'PaperUpload', 
    'PaperSummary',
    'SearchFilters',
    'SearchQuery', 
    'ParsedQueryInfo',
    'ProcessingRequest', 
    'ProcessingResponse',
    'Theme',
    'TimelinePoint',
    'TrendsAnalysis',
    'TopPaper',
    'ImageContent',
    'TableContent',
    'MultiModalContent',
    'ChunkType',
    'MultiModalChunk',
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
    'NoteListResponse',
    'DifficultyLevel',
    'QuizType',
    'QuizOption',
    'QuizQuestion',
    'QuizConfig',
    'QuizResponse',
    'QuizAttemptRequest',
    'QuizAttemptResponse',
    'QuizListResponse',
]