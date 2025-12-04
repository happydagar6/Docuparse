from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ExamType(str, Enum):
    SCHOOL_TEST = "school_test"
    COLLEGE_EXAM = "college_exam"
    COMPETITIVE = "competitive"
    CERTIFICATION = "certification"

class StudyStyle(str, Enum):
    INTENSIVE = "intensive"
    BALANCED = "balanced"
    LIGHT = "light"
    
class StudyPlanRequest(BaseModel):
    paper_id: str
    duration_weeks: int = Field(ge=1, le=12)
    exam_type: ExamType
    study_style: StudyStyle
    exam_name: Optional[str] = None
    daily_hours: Optional[int] = Field(default=2, ge=1, le=8)

class DayPlan(BaseModel):
    day: int
    topics: List[str]
    tasks: List[str]
    duration_hours: float

class WeekPlan(BaseModel):
    week: int
    focus_area: str
    days: List[DayPlan]
    goals: List[str]
    revision_topics: List[str] = []

class StudyPlanResponse(BaseModel):
    id: str
    paper_id: str
    paper_title: str
    duration_weeks: int
    exam_type: str
    study_style: str
    weeks: List[WeekPlan]
    tips: List[str]
    created_at: datetime
    
class StudyPlanDB(BaseModel):
    id: str
    user_id: Optional[str] = None
    paper_id: str
    paper_title: str
    request: StudyPlanRequest
    plan: StudyPlanResponse
    created_at: datetime