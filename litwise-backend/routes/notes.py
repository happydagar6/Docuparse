"""
Notes Routes
API endpoints for notes CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from middleware import get_current_user, AuthUser
from models import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from services.notes_service import NotesService
from workflow.db import supabase

router = APIRouter(prefix="/api/notes", tags=["notes"])


def get_notes_service() -> NotesService:
    """Dependency to get notes service instance"""
    return NotesService(supabase)


@router.get("", response_model=NoteListResponse)
async def get_notes(
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Get all notes for the current user
    
    Returns:
        NoteListResponse: List of notes with metadata
    """
    try:
        return await service.get_all_notes(current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notes: {str(e)}"
        )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Get a specific note by ID
    
    Args:
        note_id: UUID of the note
        
    Returns:
        NoteResponse: The requested note
        
    Raises:
        HTTPException: 404 if note not found
    """
    note = await service.get_note(note_id, current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found"
        )
    return note


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Create a new note
    
    Args:
        note_data: Note creation data
        
    Returns:
        NoteResponse: The created note
    """
    try:
        return await service.create_note(note_data, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(e)}"
        )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Update an existing note
    
    Args:
        note_id: UUID of the note
        note_data: Note update data
        
    Returns:
        NoteResponse: The updated note
        
    Raises:
        HTTPException: 404 if note not found
    """
    try:
        updated_note = await service.update_note(note_id, note_data, current_user.id)
        if not updated_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with id {note_id} not found"
            )
        return updated_note
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update note: {str(e)}"
        )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Delete a note
    
    Args:
        note_id: UUID of the note
        
    Raises:
        HTTPException: 404 if note not found
    """
    success = await service.delete_note(note_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found"
        )


@router.patch("/{note_id}/toggle-pin", response_model=NoteResponse)
async def toggle_pin_note(
    note_id: str,
    current_user: AuthUser = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service)
):
    """
    Toggle the pinned status of a note
    
    Args:
        note_id: UUID of the note
        
    Returns:
        NoteResponse: The note with updated pin status
        
    Raises:
        HTTPException: 404 if note not found
    """
    updated_note = await service.toggle_pin(note_id, current_user.id)
    if not updated_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found"
        )
    return updated_note
