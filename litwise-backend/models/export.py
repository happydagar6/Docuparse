"""
APA Export Models
Pydantic models for document export functionality
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Union, Literal

class ParagraphContent(BaseModel):
    """Paragraph content with optional citations"""
    type: Literal["paragraph"] = Field(default="paragraph", description="Content type identifier")
    text: str = Field(..., description="Paragraph text with citation placeholders like {{paper_id}}")
    citations: Optional[List[str]] = Field(default_factory=list, description="List of paper IDs cited in this paragraph")

class HeadingContent(BaseModel):
    """Heading content for APA 7th Edition multi-level headings"""
    type: Literal["heading"] = Field(default="heading", description="Content type identifier")
    level: int = Field(..., ge=1, le=5, description="Heading level (1-5 per APA 7th Edition)")
    text: str = Field(..., min_length=1, description="Heading text")
    
    @field_validator('level')
    def validate_level(cls, v):
        """Ensure heading level is between 1 and 5"""
        if v < 1 or v > 5:
            raise ValueError('Heading level must be between 1 and 5 (APA 7th Edition)')
        return v

class TableCell(BaseModel):
    """Individual cell in a table"""
    content: str = Field(..., description="Cell content (plain text)")
    header: bool = Field(default=False, description="Whether this is a header cell")

class TableContent(BaseModel):
    """
    Table content for research papers
    
    APA 7th Edition Table Requirements:
    - Numbered (Table 1, Table 2, etc.)
    - Title above table (italicized)
    - Double-spaced
    - Minimal horizontal lines (top, bottom, under header only)
    - No vertical lines
    - Left-aligned content
    - Note below table if needed (starts with "Note.")
    """
    type: Literal["table"] = Field(default="table", description="Content type identifier")
    number: int = Field(..., ge=1, description="Table number for ordering")
    title: str = Field(..., min_length=1, description="Table title (will be italicized)")
    rows: List[List[str]] = Field(..., min_items=1, description="Table data as list of rows")
    header_rows: int = Field(default=1, description="Number of header rows (usually 1)")
    note: Optional[str] = Field(None, description="Table note/footer (optional)")

class FigureContent(BaseModel):
    """
    Figure content for research papers
    
    APA 7th Edition Figure Requirements:
    - Numbered (Figure 1, Figure 2, etc.)
    - Caption below figure (starts with 'Figure #.')
    - Caption is in sentence case
    - Figure positioned near relevant text
    - All figures referenced in text
    - Supported formats: JPEG, PNG, GIF, WebP, SVG
    """
    type: Literal["figure"] = Field(default="figure", description="Content type identifier")
    number: int = Field(..., ge=1, description="Figure number for ordering")
    file_id: str = Field(..., description="File ID from media upload endpoint")
    filename: str = Field(..., description="Original filename")
    caption: str = Field(..., min_length=1, description="Figure caption (APA sentence case)")
    alt_text: Optional[str] = Field(None, description="Alternative text for accessibility")
    width_percent: Optional[int] = Field(default=100, ge=10, le=100, description="Figure width as % of page (10-100)")

class ReferenceMetadata(BaseModel):
    """Metadata for a single reference (APA 7th Edition compliant)"""
    title: str = Field(..., description="Paper title")
    author_list: List[str] = Field(..., description="List of author names")
    year: Optional[str] = Field("n.d.", description="Publication year")
    doi: Optional[str] = Field(None, description="DOI identifier")
    publisher: Optional[str] = Field(None, description="Publisher or journal name")
    volume: Optional[str] = Field(None, description="Journal volume number (italicized in APA)")
    issue: Optional[str] = Field(None, description="Journal issue number (in parentheses, not italicized)")
    pages: Optional[str] = Field(None, description="Page range (e.g., '123-145' or 'e1234')")
    publication_type: Optional[str] = Field("journal", description="Type: 'journal', 'book', 'webpage', etc.")

class APAExportRequest(BaseModel):
    """Request model for APA document export"""
    title: str = Field(..., min_length=1, description="Paper title")
    running_head: str = Field(..., max_length=50, description="Short title for header (max 50 chars)")
    authors: List[str] = Field(..., min_items=1, description="List of author names")
    affiliation: Optional[str] = Field("Independent Researcher", description="Author affiliation")
    abstract: Optional[str] = Field(None, description="Abstract text (max 250 words recommended)")
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords (3-5 recommended)")
    content: List[Union[ParagraphContent, HeadingContent, TableContent, FigureContent]] = Field(..., min_items=1, description="List of content items (paragraphs, headings, tables, and figures)")
    references_metadata: Dict[str, ReferenceMetadata] = Field(
        default_factory=dict,
        description="Map of paper_id to reference metadata"
    )
    
    @field_validator('running_head')
    def validate_running_head(cls, v):
        if len(v) > 50:
            raise ValueError('Running head must be 50 characters or less')
        return v
    
    @field_validator('abstract')
    def validate_abstract(cls, v):
        """Validate abstract length (250 words max recommended by APA 7th)"""
        if v:
            word_count = len(v.split())
            if word_count > 300:
                raise ValueError(f'Abstract is too long ({word_count} words). Maximum 250 words recommended.')
        return v
    
    @field_validator('keywords')
    def validate_keywords(cls, v):
        """Validate keywords list (3-5 recommended)"""
        if v and len(v) > 10:
            raise ValueError('Too many keywords. Maximum 10 keywords allowed.')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Impact of Machine Learning on Healthcare",
                "running_head": "ML IN HEALTHCARE",
                "authors": ["John Smith", "Jane Doe"],
                "affiliation": "Stanford University",
                "abstract": "This study examines the transformative role of machine learning in modern healthcare systems. We analyze recent developments and their implications for clinical practice.",
                "keywords": ["machine learning", "healthcare", "artificial intelligence", "clinical applications"],
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
                        "publisher": "Nature Medicine",
                        "volume": "45",
                        "issue": "3",
                        "pages": "123-145",
                        "publication_type": "journal"
                    }
                }
            }
        }
    )