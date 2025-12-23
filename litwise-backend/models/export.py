"""
APA Export Models
Pydantic models for document export functionality
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict

class ParagraphContent(BaseModel):
    """Paragraph content with optional citations"""
    text: str = Field(..., description="Paragraph text with citation placeholders like {{paper_id}}")
    citations: Optional[List[str]] = Field(default_factory=list, description="List of paper IDs cited in this paragraph")

class ReferenceMetadata(BaseModel):
    """Metadata for a single reference"""
    title: str = Field(..., description="Paper title")
    author_list: List[str] = Field(..., description="List of author names")
    year: Optional[str] = Field("n.d.", description="Publication year")
    doi: Optional[str] = Field(None, description="DOI identifier")
    publisher: Optional[str] = Field(None, description="Publisher or journal name")

class APAExportRequest(BaseModel):
    """Request model for APA document export"""
    title: str = Field(..., min_length=1, description="Paper title")
    running_head: str = Field(..., max_length=50, description="Short title for header (max 50 chars)")
    authors: List[str] = Field(..., min_items=1, description="List of author names")
    affiliation: Optional[str] = Field("Independent Researcher", description="Author affiliation")
    content: List[ParagraphContent] = Field(..., min_items=1, description="List of paragraph objects")
    references_metadata: Dict[str, ReferenceMetadata] = Field(
        default_factory=dict,
        description="Map of paper_id to reference metadata"
    )
    
    @field_validator('running_head')
    def validate_running_head(cls, v):
        if len(v) > 50:
            raise ValueError('Running head must be 50 characters or less')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Impact of Machine Learning on Healthcare",
                "running_head": "ML IN HEALTHCARE",
                "authors": ["John Smith", "Jane Doe"],
                "affiliation": "Stanford University",
                "content": [
                    {
                        "text": "Machine learning has revolutionized healthcare {{paper_123}}. Recent studies show significant improvements {{paper_456}}.",
                        "citations": ["paper_123", "paper_456"]
                    }
                ],
                "references_metadata": {
                    "paper_123": {
                        "title": "Deep Learning in Medical Imaging",
                        "author_list": ["Smith, A.", "Jones, B."],
                        "year": "2021",
                        "doi": "10.1234/example",
                        "publisher": "Nature Medicine"
                    }
                }
            }
        }
    )