from pydantic import BaseModel
from typing import List, Optional
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
    
