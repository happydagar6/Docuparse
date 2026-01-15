from pydantic import BaseModel, Field, field_validator, ConfigDict
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

    @field_validator('year_to', mode='after')
    @classmethod
    def validate_year_range(cls, v, info):
        if v is not None and 'year_from' in info.data and info.data['year_from'] is not None:
            if v < info.data['year_from']:
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

