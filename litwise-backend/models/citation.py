from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum


class CitationFormat(str, Enum):
    APA = "apa"
    IEEE = "ieee"
    BIBTEX = "bibtex"
    VANCOUVER = "vancouver"
    MLA = "mla"
    

class PaperMetadata(BaseModel):
    id: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None


class CitationRequest(BaseModel):
    paper_id: str
    format: CitationFormat = CitationFormat.APA
    
class BatchCitationRequest(BaseModel):
    paper_ids: List[str]
    format: CitationFormat = CitationFormat.APA
    
class CitationResponse(BaseModel):
    paper_id: str
    format: str
    citation: str
    raw_metadata: Optional[PaperMetadata] = None
    



# Enhanced Citation Models
class ExtractedCitation(BaseModel):
    """Citation extracted from a paper"""
    id: Optional[str] = None
    paper_id: str
    citation_text: str
    in_text_refs: List[str] = []
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    relevance_summary: Optional[str] = None
    citation_context: List[str] = []
    mention_count: int = 1
    importance_score: float = 0.0
    citation_type: Optional[str] = None
    verified: bool = False

class ExtractCitationsRequest(BaseModel):
    """Request to extract citations from a paper"""
    paper_id: str
    use_ai_enrichment: bool = True

class ExtractCitationsResponse(BaseModel):
    """Response with extracted citations"""
    paper_id: str
    citations_extracted: int
    citations: List[ExtractedCitation]
    extraction_time: float

class CitationStatsResponse(BaseModel):
    """Statistics about paper citations"""
    paper_id: str
    total_citations: int
    citations_by_type: Dict[str, int]
    top_cited_works: List[Dict]
    average_citation_year: Optional[float]