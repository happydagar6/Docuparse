from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class AuthorInfo(BaseModel):
    """Author information structure"""
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None

class PaperMetadata(BaseModel):
    """Extended metadata for research papers"""
    authors: Optional[List[AuthorInfo]] = Field(default_factory=list, description="List of paper authors")
    publication_year: Optional[int] = Field(None, ge=1900, le=2100, description="Year of publication")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    keywords: Optional[List[str]] = Field(default_factory=list, description="Paper keywords/tags")
    journal_or_conference: Optional[str] = Field(None, description="Publication venue")
    abstract: Optional[str] = Field(None, description="Paper abstract")

    @field_validator('publication_year')
    def validate_year(cls, v):
        if v is not None and (v < 1900 or v > 2100):
            raise ValueError('Publication year must be between 1900 and 2100')
        return v

class PaperUpload(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    metadata: Optional[PaperMetadata] = Field(None, description="Optional paper metadata")
    # File handled separately in the route

class PaperSummary(BaseModel):
    key_points: List[str]
    citations: List[str]
    related_works: List[str]

class SearchFilters(BaseModel):
    """Advanced search filters"""
    author: Optional[str] = Field(None, description="Filter by author name (partial match)")
    year_from: Optional[int] = Field(None, ge=1900, le=2100, description="Filter by publication year (from)")
    year_to: Optional[int] = Field(None, ge=1900, le=2100, description="Filter by publication year (to)")
    keywords: Optional[List[str]] = Field(default_factory=list, description="Filter by keywords")
    paper_ids: Optional[List[str]] = Field(default_factory=list, description="Filter by specific paper IDs")
    
    # Phase 1.1: Content filters
    has_images: Optional[bool] = Field(None, description="Filter papers with extracted images")
    has_tables: Optional[bool] = Field(None, description="Filter papers with extracted tables")
    has_equations: Optional[bool] = Field(None, description="Filter papers with equations/formulas")
    
    # Phase 1.2: Venue filter
    venue: Optional[str] = Field(None, description="Filter by conference or journal name")

    @field_validator('year_to')
    def validate_year_range(cls, v, values):
        if v is not None and 'year_from' in values and values['year_from'] is not None:
            if v < values['year_from']:
                raise ValueError('year_to must be greater than or equal to year_from')
        return v
    
class SearchQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)  # Accept both snake_case and camelCase
    
    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    debug: Optional[bool] = Field(default=False, description="Enable debug mode for diagnostics")
    filters: Optional[SearchFilters] = Field(None, description="Advanced search filters")
    use_nl_parsing: Optional[bool] = Field(default=True, description="Enable natural language query parsing")

class ParsedQueryInfo(BaseModel):
    """Information about parsed natural language query"""
    original_query: str = Field(..., description="Original user query")
    semantic_query: str = Field(..., description="Cleaned query for semantic search")
    parsed_filters: SearchFilters = Field(..., description="Extracted filters")
    parsed_elements: List[str] = Field(default_factory=list, description="Human-readable parsed elements")
    confidence: float = Field(..., ge=0, le=1, description="Parsing confidence (0-1)")

class ProcessingRequest(BaseModel):
    paper_id: str = Field(..., description="ID of the paper to process")

class ProcessingResponse(BaseModel):
    id: str
    status: str
    message: str
    summary: Optional[dict] = None

# ============================================
# SYNTHESIS MODELS (Phase 1)
# ============================================

class Theme(BaseModel):
    """Represents a research theme identified across papers"""
    name: str = Field(..., description="Theme name (e.g., 'Deep Learning', 'Attention Mechanisms')")
    description: str = Field(..., description="Brief description of the theme")
    count: int = Field(..., ge=0, description="Number of papers discussing this theme")
    papers: List[str] = Field(default_factory=list, description="Paper IDs associated with this theme")

class TimelinePoint(BaseModel):
    """Publication timeline data point"""
    year: int = Field(..., description="Publication year")
    count: int = Field(..., ge=0, description="Number of papers published in this year")

class TrendsAnalysis(BaseModel):
    """Temporal trends in research publications"""
    timeline: List[TimelinePoint] = Field(default_factory=list, description="Year-by-year publication counts")
    trend_description: str = Field(..., description="Human-readable trend summary")

class TopPaper(BaseModel):
    """Top paper with relevance score"""
    id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    relevance: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    year: Optional[int] = Field(None, description="Publication year")

class SynthesisRequest(BaseModel):
    """Request to synthesize search results"""
    query: str = Field(..., min_length=1, description="Original search query")
    search_results: List[Dict[str, Any]] = Field(..., description="Search results to synthesize")
    
    @field_validator('search_results')
    def validate_results(cls, v):
        if not v or len(v) == 0:
            raise ValueError('search_results cannot be empty')
        return v

class SynthesisResponse(BaseModel):
    """AI-generated research synthesis"""
    query: str = Field(..., description="Original search query")
    paper_count: int = Field(..., ge=0, description="Number of papers analyzed")
    themes: List[Theme] = Field(default_factory=list, description="Main themes identified")
    key_findings: List[str] = Field(default_factory=list, description="Key findings across papers")
    research_gaps: List[str] = Field(default_factory=list, description="Identified research gaps")
    trends: TrendsAnalysis = Field(..., description="Temporal trends analysis")
    top_papers: List[TopPaper] = Field(default_factory=list, description="Most relevant papers")
    generated_at: str = Field(..., description="ISO timestamp of synthesis generation")
    
    
class ImageContent(BaseModel):
    """Extracted image with metadata"""
    page: int
    image_index: int
    width: int
    height: int
    format: str
    caption: Optional[str] = None
    image_base64: Optional[str] = None  # Only sent when needed
    hash: str
    size_kb: float

class TableContent(BaseModel):
    """Extracted table with metadata"""
    page: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    row_count: int
    col_count: int
    text_representation: str
    hash: str
    
class MultiModalContent(BaseModel):
    """Complete multi-modal extraction result"""
    images: List[ImageContent] = Field(default_factory=list)
    tables: List[TableContent] = Field(default_factory=list)
    total_items: int = 0
    
class ChunkType(str, Enum):
    """Type of content chunk"""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    
class MultiModalChunk(BaseModel):
    """Unified chunk that can be text, image, or table"""
    chunk_id: str
    type: ChunkType
    content: str  # Text content or caption
    page: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Type-specific fields
    image_data: Optional[ImageContent] = None
    table_data: Optional[TableContent] = None
    

# ============================================
# NOTES MODELS
# ============================================

class NoteBase(BaseModel):
    """Base note model with common fields"""
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(default="", max_length=10000, description="Note content")
    color: Optional[str] = Field(default="#fef3c7", description="Note color for UI")
    pinned: bool = Field(default=False, description="Whether note is pinned")

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Validate title is not empty or whitespace"""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> str:
        """Validate color is a valid hex color"""
        if v is None:
            return "#fef3c7"
        if not v.startswith('#') or len(v) not in [4, 7]:
            raise ValueError('Color must be a valid hex color (e.g., #fff or #ffffff)')
        return v


class NoteCreate(NoteBase):
    """Model for creating a new note"""
    pass


class NoteUpdate(BaseModel):
    """Model for updating an existing note"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=10000)
    color: Optional[str] = None
    pinned: Optional[bool] = None

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate title is not empty or whitespace if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is a valid hex color if provided"""
        if v is not None and (not v.startswith('#') or len(v) not in [4, 7]):
            raise ValueError('Color must be a valid hex color (e.g., #fff or #ffffff)')
        return v


class NoteResponse(NoteBase):
    """Model for note responses"""
    id: str = Field(..., description="Note UUID")
    user_id: str = Field(..., description="User UUID who owns the note")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Model for list of notes response"""
    notes: list[NoteResponse]
    total: int
    pinned_count: int
