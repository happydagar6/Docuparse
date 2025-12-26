"""
Notes Service
Business logic for notes CRUD operations
"""

from typing import Optional
from supabase import Client
from models import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from datetime import datetime


class NotesService:
    """Service class for managing user notes"""

    def __init__(self, supabase_client: Client):
        """
        Initialize notes service
        
        Args:
            supabase_client: Authenticated Supabase client
        """
        self.supabase = supabase_client

    async def get_all_notes(self, user_id: str) -> NoteListResponse:
        """
        Get all notes for a user
        
        Args:
            user_id: UUID of the user
            
        Returns:
            NoteListResponse with list of notes and counts
        """
        # Fetch all notes for user, ordered by pinned status and creation date
        response = self.supabase.table('notes')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('pinned', desc=True)\
            .order('created_at', desc=True)\
            .execute()

        notes = [NoteResponse(**note) for note in response.data]
        pinned_count = sum(1 for note in notes if note.pinned)

        return NoteListResponse(
            notes=notes,
            total=len(notes),
            pinned_count=pinned_count
        )

    async def get_note(self, note_id: str, user_id: str) -> Optional[NoteResponse]:
        """
        Get a specific note by ID
        
        Args:
            note_id: UUID of the note
            user_id: UUID of the user (for authorization)
            
        Returns:
            NoteResponse if found, None otherwise
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
        Create a new note
        
        Args:
            note_data: Note creation data
            user_id: UUID of the user
            
        Returns:
            NoteResponse of created note
        """
        note_dict = note_data.model_dump()
        note_dict['user_id'] = user_id

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
        Update an existing note
        
        Args:
            note_id: UUID of the note
            note_data: Note update data
            user_id: UUID of the user (for authorization)
            
        Returns:
            NoteResponse if updated successfully, None if not found
        """
        # Only include fields that were actually provided
        update_dict = note_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            # No fields to update, just return current note
            return await self.get_note(note_id, user_id)

        # Update the note
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
        Delete a note
        
        Args:
            note_id: UUID of the note
            user_id: UUID of the user (for authorization)
            
        Returns:
            True if deleted successfully, False otherwise
        """
        response = self.supabase.table('notes')\
            .delete()\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .execute()

        return len(response.data) > 0

    async def toggle_pin(self, note_id: str, user_id: str) -> Optional[NoteResponse]:
        """
        Toggle the pinned status of a note
        
        Args:
            note_id: UUID of the note
            user_id: UUID of the user (for authorization)
            
        Returns:
            NoteResponse with updated pin status, None if not found
        """
        # Get current note
        current_note = await self.get_note(note_id, user_id)
        if not current_note:
            return None

        # Toggle pinned status
        response = self.supabase.table('notes')\
            .update({'pinned': not current_note.pinned})\
            .eq('id', note_id)\
            .eq('user_id', user_id)\
            .execute()

        if response.data:
            return NoteResponse(**response.data[0])
        return None
