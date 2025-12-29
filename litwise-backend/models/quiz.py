"""
Quiz Generator Models
Pydantic models for quiz configuration and responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    """Quiz difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    
class QuizType(str, Enum):
    """Types of quizzes"""
    FACT_BASED = "fact_based" # Recall-based questions
    SCENARIO_BASED = "scenario_based" # Application-based questions
    MIXED = "mixed" # Combination of both types
    
class QuizOption(BaseModel):
    """Multiple choice option"""
    text: str = Field(..., description="Option text")
    is_correct: bool = Field(..., description="Whether this is the correct answer")

class QuizQuestion(BaseModel):
    """Single quiz question with multiple choice answers"""
    question_text: str = Field(..., description="The question")
    options: List[str] = Field(..., min_items=4, max_items=4, description="4 multiple choice options")
    correct_answer_index: int = Field(..., ge=0, le=3, description="Index of correct answer (0-3)")
    explanation: str = Field(..., description="Detailed explanation of the correct answer")
    source_citation: str = Field(..., description="Citation/reference from the source material")
    source_page: Optional[int] = Field(None, description="Page number in source document")
    difficulty: DifficultyLevel = Field(..., description="Question difficulty")
    quiz_type: QuizType = Field(..., description="Type of question")
    
    
class QuizConfig(BaseModel):
    """Quiz generation configuration"""
    paper_id: str = Field(..., description="ID of the paper to generate quiz from")
    title: str = Field(..., min_length=3, max_length=200, description="Quiz title")
    description: Optional[str] = Field(None, max_length=500, description="Quiz description")
    difficulty_level: DifficultyLevel = Field(..., description="Overall difficulty level")
    topic: str = Field(..., min_length=3, max_length=200, description="Specific topic to focus on")
    question_count: int = Field(..., ge=5, le=50, description="Number of questions (5-50)")
    quiz_type: QuizType = Field(..., description="Type of quiz to generate")


class RetrievalContext(BaseModel):
    """Context chunk retrieved from vector database"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    paper_id: str = Field(..., description="Paper ID")
    content: str = Field(..., description="Chunk text content")
    page: Optional[int] = Field(None, description="Page number")
    similarity_score: float = Field(..., ge=0, le=1, description="Relevance score")
    
    
class QuizResponse(BaseModel):
    """Generated quiz response"""
    id: str = Field(..., description="Quiz ID")
    user_id: str = Field(..., description="User ID")
    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Quiz title")
    description: Optional[str] = Field(None)
    difficulty_level: DifficultyLevel = Field(...)
    topic: str = Field(...)
    question_count: int = Field(...)
    quiz_type: QuizType = Field(...)
    questions: List[QuizQuestion] = Field(..., description="List of quiz questions")
    retrieval_context: List[RetrievalContext] = Field(..., description="Source chunks used")
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)