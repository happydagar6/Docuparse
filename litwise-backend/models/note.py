"""
Note Models
Pydantic models for notes functionality
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class NoteBase(BaseModel):
    """Base note model with common fields"""
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(default="", max_length=10000, description="Note content")
    color: Optional[str] = Field(default="#fef3c7", description="Note color for UI")
    pinned: bool = Field(default=False, description="Whether note is pinned")

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Validate title is not empty or whitespace"""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> str:
        """Validate color is a valid hex color"""
        if v is None:
            return "#fef3c7"
        if not v.startswith('#') or len(v) not in [4, 7]:
            raise ValueError('Color must be a valid hex color (e.g., #fff or #ffffff)')
        return v


class NoteCreate(NoteBase):
    """Model for creating a new note"""
    pass


class NoteUpdate(BaseModel):
    """Model for updating an existing note"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=10000)
    color: Optional[str] = None
    pinned: Optional[bool] = None

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate title is not empty or whitespace if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is a valid hex color if provided"""
        if v is not None and (not v.startswith('#') or len(v) not in [4, 7]):
            raise ValueError('Color must be a valid hex color (e.g., #fff or #ffffff)')
        return v


class NoteResponse(NoteBase):
    """Model for note responses"""
    id: str = Field(..., description="Note UUID")
    user_id: str = Field(..., description="User UUID who owns the note")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Model for list of notes response"""
    notes: list[NoteResponse]
    total: int
    pinned_count: int
