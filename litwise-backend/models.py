from pydantic import BaseModel, Field, validator
from typing import List, TypedDict, Optional, Dict, Any
from fastapi import UploadFile

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

    @validator('publication_year')
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

    @validator('year_to')
    def validate_year_range(cls, v, values):
        if v is not None and 'year_from' in values and values['year_from'] is not None:
            if v < values['year_from']:
                raise ValueError('year_to must be greater than or equal to year_from')
        return v
    
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    debug: Optional[bool] = Field(default=False, description="Enable debug mode for diagnostics")
    filters: Optional[SearchFilters] = Field(None, description="Advanced search filters")

class ProcessingRequest(BaseModel):
    paper_id: str = Field(..., description="ID of the paper to process")

class ProcessingResponse(BaseModel):
    id: str
    status: str
    message: str
    summary: Optional[dict] = None
    