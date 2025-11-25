from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import UploadFile

class PaperUpload(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    # File handled separately in the route
    

class PaperSummary(BaseModel):
    key_points: List[str]
    citations: List[str]
    related_works: List[str]
    
class SearchQuery(BaseModel):
    query: str
    limit: int = 5
    debug: Optional[bool] = False

class ProcessingRequest(BaseModel):
    paper_id: str = Field(..., description="ID of the paper to process")

class ProcessingResponse(BaseModel):
    id: str
    status: str
    message: str
    summary: Optional[dict] = None