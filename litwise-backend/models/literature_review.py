from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ReviewStyle(str, Enum):
    NARRATIVE = "narrative"
    SYSTEMATIC = "systematic"
    CRITICAL = "critical"
    

class ReviewSection(str, Enum):
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    THEMATIC_ANALYSIS = "thematic_analysis"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    
    
class LiteratureReviewRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=1, max_length=20)
    topic: str = Field(..., min_length=5, max_length=800)
    review_style: ReviewStyle = ReviewStyle.NARRATIVE
    include_sections: List[ReviewSection] = Field(
        default=[
            ReviewSection.INTRODUCTION,
            ReviewSection.METHODOLOGY,
            ReviewSection.THEMATIC_ANALYSIS,
            ReviewSection.DISCUSSION,
            ReviewSection.CONCLUSION,
            ReviewSection.REFERENCES,
        ]
    )
    word_limit: Optional[int] = Field(default=3000, ge=800, le=10000)
    focus_areas: Optional[List[str]] = None
    
    
class ThemeAnalysis(BaseModel):
    theme_name: str
    description: str
    supporting_papers: List[str]
    key_points: List[str]
    

class ReviewContent(BaseModel):
    introduction: Optional[str] = None
    methodology: Optional[str] = None
    thematic_analysis: Optional[List[ThemeAnalysis]] = None
    discussion: Optional[str] = None
    conclusion: Optional[str] = None
    references: Optional[List[str]] = None
    source_coverage_note: Optional[str] = None  # Notes on what sources covered vs. gaps
    
    
class LiteratureReviewResponse(BaseModel):
    id: str
    topic: str
    review_style: str
    paper_count: int
    content: ReviewContent
    word_count: int
    created_at: datetime
    
    
class LiteratureReviewDB(BaseModel):
    id: str
    topic: str
    review_style: str
    paper_ids: List[str]
    paper_count: int
    content: dict
    word_count: int
    created_at: datetime