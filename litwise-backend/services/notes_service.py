"""
=============================================================================
Notes Service (`services/notes_service.py`)
=============================================================================
This service provides full CRUD (Create, Read, Update, Delete) business logic 
for user research notes and draft documents stored in Supabase PostgreSQL.

Architectural Patterns:
1. Service Layer Pattern: Decouples API route handlers (`routes/notes.py`) from 
   database access logic.
2. Row-Level Authorization: Every database query enforces `.eq('user_id', user_id)` 
   to prevent unauthorized data access across users.
3. Partial Updates (PATCH): Uses Pydantic's `exclude_unset=True` in `update_note` 
   so only updated fields are modified in SQL.
4. Smart Sorting: Orders notes with pinned items first (`pinned DESC`) followed 
   by creation date (`created_at DESC`).
=============================================================================
"""

from typing import Optional
from supabase import Client
from models import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from datetime import datetime


class NotesService:
    """Service class for managing user research notes in Supabase PostgreSQL."""

    def __init__(self, supabase_client: Client):
        """
        Initialize notes service with an authenticated Supabase DB client.
        
        Args:
            supabase_client: Authenticated Supabase client instance
        """
        self.supabase = supabase_client

    async def get_all_notes(self, user_id: str) -> NoteListResponse:
        """
        Get all notes for a specific user.
        
        Sorting Strategy:
        1. Pinned notes appear at the top (`order('pinned', desc=True)`).
        2. Within each group, newest notes appear first (`order('created_at', desc=True)`).
        
        Args:
            user_id: UUID of the authenticated user
            
        Returns:
            NoteListResponse containing list of notes, total count, and pinned count.
        """
        # Execute Supabase SQL query with user_id filter and multi-column ordering
        response = self.supabase.table('notes')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('pinned', desc=True)\
            .order('created_at', desc=True)\
            .execute()

        # Map database JSON rows into Pydantic models
        notes = [NoteResponse(**note) for note in response.data]
        pinned_count = sum(1 for note in notes if note.pinned)

        return NoteListResponse(
            notes=notes,
            total=len(notes),
            pinned_count=pinned_count
        )

    async def get_note(self, note_id: str, user_id: str) -> Optional[NoteResponse]:
        """
        Get a single note by ID with ownership verification.
        
        Args:
            note_id: UUID of the target note
            user_id: UUID of the requesting user (for authorization)
            
        Returns:
            NoteResponse if found and authorized, None otherwise.
        """
        response = self.supabase.table('notes')\
            .select('*')\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()

        if response.data:
            return NoteResponse(**response.data)
        return None

    async def create_note(self, note_data: NoteCreate, user_id: str) -> NoteResponse:
        """
        Create a new research note.
        
        Args:
            note_data: Pydantic creation model (title, content, tags, pinned)
            user_id: UUID of the note owner
            
        Returns:
            NoteResponse model of the newly created note.
        """
        # Convert Pydantic model to dictionary and inject user_id
        note_dict = note_data.model_dump()
        note_dict['user_id'] = user_id

        # Insert record into Supabase 'notes' table
        response = self.supabase.table('notes')\
            .insert(note_dict)\
            .execute()

        if not response.data:
            raise ValueError("Failed to create note")

        return NoteResponse(**response.data[0])

    async def update_note(
        self,
        note_id: str,
        note_data: NoteUpdate,
        user_id: str
    ) -> Optional[NoteResponse]:
        """
        Update an existing note (supports partial updates).
        
        Args:
            note_id: UUID of the note to update
            note_data: Pydantic update model with optional fields
            user_id: UUID of the user (for authorization)
            
        Returns:
            Updated NoteResponse model, or None if not found/unauthorized.
        """
        # exclude_unset=True ensures we ONLY update fields that were explicitly sent in the API request
        update_dict = note_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            # If no fields provided in payload, return existing note without making SQL UPDATE call
            return await self.get_note(note_id, user_id)

        # Execute UPDATE query matching both note_id AND user_id
        response = self.supabase.table('notes')\
            .update(update_dict)\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .execute()

        if response.data:
            return NoteResponse(**response.data[0])
        return None

    async def delete_note(self, note_id: str, user_id: str) -> bool:
        """
        Delete a note by ID with user ownership check.
        
        Args:
            note_id: UUID of the note to delete
            user_id: UUID of the user (for authorization)
            
        Returns:
            True if a record was deleted, False otherwise.
        """
        response = self.supabase.table('notes')\
            .delete()\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .execute()

        return len(response.data) > 0

    async def toggle_pin(self, note_id: str, user_id: str) -> Optional[NoteResponse]:
        """
        Toggle the pinned status of a note (Pin/Unpin).
        
        Args:
            note_id: UUID of the note
            user_id: UUID of the user (for authorization)
            
        Returns:
            Updated NoteResponse model, or None if not found/unauthorized.
        """
        # Fetch current note to inspect current 'pinned' boolean state
        current_note = await self.get_note(note_id, user_id)
        if not current_note:
            return None

        # Flip the boolean value (`not current_note.pinned`)
        response = self.supabase.table('notes')\
            .update({'pinned': not current_note.pinned})\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .execute()

        if response.data:
            return NoteResponse(**response.data[0])
        return None
