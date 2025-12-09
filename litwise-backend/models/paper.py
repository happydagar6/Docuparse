from pydantic import BaseModel, Field, validator, ConfigDict
from typing import List, Optional, Dict, Any
from fastapi import UploadFile

class PaperUpload(BaseModel):
    title: str = Field(..., description="Title of the research paper")
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
    has_images: Optional[bool] = Field(None, description="Filter papers with extracted images")
    has_tables: Optional[bool] = Field(None, description="Filter papers with extracted tables")
    has_equations: Optional[bool] = Field(None, description="Filter papers with equations/formulas")
    venue: Optional[str] = Field(None, description="Filter by conference or journal name")

    @validator('year_to')
    def validate_year_range(cls, v, values):
        if v is not None and 'year_from' in values and values['year_from'] is not None:
            if v < values['year_from']:
                raise ValueError('year_to must be greater than or equal to year_from')
        return v
    
class SearchQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    debug: Optional[bool] = Field(default=False, description="Enable debug mode for diagnostics")
    filters: Optional[SearchFilters] = Field(None, description="Advanced search filters")
    use_nl_parsing: Optional[bool] = Field(default=True, description="Enable natural language query parsing")

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
    max_papers: int = Field(default=20, ge=10, le=100, description="Maximum number of chunks to analyze (10-100)")
    
    @validator('search_results')
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


# ============================================
# SYNTHESIS HISTORY MODELS
# ============================================

class SynthesisHistoryItem(BaseModel):
    """Saved synthesis from history"""
    id: str = Field(..., description="Synthesis history ID")
    query: str = Field(..., description="Original search query")
    paper_count: int = Field(..., ge=0, description="Number of papers analyzed")
    max_papers: int = Field(..., description="Maximum papers setting used")
    themes: List[Theme] = Field(default_factory=list, description="Main themes identified")
    key_findings: List[str] = Field(default_factory=list, description="Key findings")
    research_gaps: List[str] = Field(default_factory=list, description="Research gaps")
    trends: TrendsAnalysis = Field(..., description="Temporal trends")
    top_papers: List[TopPaper] = Field(default_factory=list, description="Most relevant papers")
    paper_ids: List[str] = Field(default_factory=list, description="Paper IDs used")
    tags: List[str] = Field(default_factory=list, description="Custom tags")
    created_at: str = Field(..., description="ISO timestamp when saved")
    updated_at: str = Field(..., description="ISO timestamp of last update")

class SynthesisHistoryListItem(BaseModel):
    """Lightweight synthesis history item for list view"""
    id: str = Field(..., description="Synthesis history ID")
    query: str = Field(..., description="Original search query")
    paper_count: int = Field(..., description="Number of papers analyzed")
    theme_count: int = Field(..., description="Number of themes identified")
    tags: List[str] = Field(default_factory=list, description="Custom tags")
    created_at: str = Field(..., description="ISO timestamp when saved")

class SaveSynthesisRequest(BaseModel):
    """Request to save a synthesis to history"""
    synthesis: SynthesisResponse = Field(..., description="Synthesis data to save")
    search_results: List[Dict[str, Any]] = Field(..., description="Original search results")
    max_papers: int = Field(default=20, description="Max papers setting used")
    tags: List[str] = Field(default_factory=list, description="Optional tags for organization")

class UpdateSynthesisTagsRequest(BaseModel):
    """Request to update tags on a saved synthesis"""
    tags: List[str] = Field(..., description="New tags to set")