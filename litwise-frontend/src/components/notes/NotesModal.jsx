/**
 * Notes Modal Component
 * Modal for managing research notes with CRUD operations
 */

'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
    Plus, 
    Pin, 
    PinOff, 
    Edit2, 
    Trash2, 
    Save, 
    X, 
    Loader2,
    StickyNote,
} from 'lucide-react';
import { toast } from 'sonner';
import { 
    getNotes, 
    createNote, 
    updateNote, 
    deleteNote, 
    togglePinNote 
} from '@/lib/notes-api';

// Color options for notes
const NOTE_COLORS = [
    { name: 'Yellow', value: '#fef3c7' },
    { name: 'Blue', value: '#dbeafe' },
    { name: 'Green', value: '#d1fae5' },
    { name: 'Pink', value: '#fce7f3' },
    { name: 'Purple', value: '#e9d5ff' },
    { name: 'Orange', value: '#fed7aa' },
];

export default function NotesModal({ isOpen, onClose }) {
    const [notes, setNotes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [editingNote, setEditingNote] = useState(null);
    const [isCreating, setIsCreating] = useState(false);
    
    // Form state
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [selectedColor, setSelectedColor] = useState(NOTE_COLORS[0].value);

    // Load notes when modal opens
    useEffect(() => {
        if (isOpen) {
            loadNotes();
        }
    }, [isOpen]);

    const loadNotes = async () => {
        setIsLoading(true);
        try {
            const response = await getNotes();
            setNotes(response.notes || []);
        } catch (error) {
            console.error('Failed to load notes:', error);
            toast.error('Failed to load notes. Please try again.');
            // Set notes to empty array on error to allow user to still interact
            setNotes([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateNew = () => {
        setIsCreating(true);
        setEditingNote(null);
        setTitle('');
        setContent('');
        setSelectedColor(NOTE_COLORS[0].value);
    };

    const handleEditNote = (note) => {
        setEditingNote(note);
        setIsCreating(false);
        setTitle(note.title);
        setContent(note.content);
        setSelectedColor(note.color);
    };

    const handleCancelEdit = () => {
        setIsCreating(false);
        setEditingNote(null);
        setTitle('');
        setContent('');
        setSelectedColor(NOTE_COLORS[0].value);
    };

    const handleSaveNote = async () => {
        if (!title.trim()) {
            toast.error('Please enter a note title');
            return;
        }

        try {
            const noteData = {
                title: title.trim(),
                content: content.trim(),
                color: selectedColor,
            };

            if (editingNote) {
                // Update existing note
                const updatedNote = await updateNote(editingNote.id, noteData);
                setNotes(notes.map(n => n.id === updatedNote.id ? updatedNote : n));
                toast.success('Note updated successfully');
            } else {
                // Create new note
                const newNote = await createNote(noteData);
                setNotes([newNote, ...notes]);
                toast.success('Note created successfully');
            }

            handleCancelEdit();
        } catch (error) {
            console.error('Failed to save note:', error);
            toast.error('Failed to save note. Please try again.');
        }
    };

    const handleDeleteNote = async (noteId) => {
        // Show a confirmation toast with action
        toast('Are you sure you want to delete this note?', {
            action: {
                label: 'Delete',
                onClick: async () => {
                    try {
                        await deleteNote(noteId);
                        setNotes(notes.filter(n => n.id !== noteId));
                        toast.success('Note deleted successfully');
                        
                        // If we were editing this note, cancel the edit
                        if (editingNote?.id === noteId) {
                            handleCancelEdit();
                        }
                    } catch (error) {
                        console.error('Failed to delete note:', error);
                        toast.error('Failed to delete note. Please try again.');
                    }
                }
            },
            cancel: {
                label: 'Cancel',
            },
        });
    };

    const handleTogglePin = async (note) => {
        try {
            const updatedNote = await togglePinNote(note.id);
            setNotes(notes.map(n => n.id === updatedNote.id ? updatedNote : n));
            toast.success(updatedNote.pinned ? 'Note pinned' : 'Note unpinned');
        } catch (error) {
            console.error('Failed to toggle pin:', error);
            toast.error('Failed to toggle pin. Please try again.');
        }
    };

    const renderNoteCard = (note) => (
        <div
            key={note.id}
            className="relative rounded-lg p-4 shadow-md border border-gray-200 dark:border-gray-700 transition-all hover:shadow-lg"
            style={{ backgroundColor: note.color }}
        >
            {/* Pin indicator */}
            {note.pinned && (
                <div className="absolute top-2 right-2">
                    <Pin className="h-4 w-4 text-gray-600 fill-current" />
                </div>
            )}

            {/* Note content */}
            <h3 className="font-semibold text-gray-900 mb-2 pr-6">
                {note.title}
            </h3>
            <p className="text-sm text-gray-700 whitespace-pre-wrap mb-3 line-clamp-4">
                {note.content || 'No content'}
            </p>

            {/* Timestamp */}
            <p className="text-xs text-gray-500 mb-3">
                {new Date(note.updated_at).toLocaleDateString()} {new Date(note.updated_at).toLocaleTimeString()}
            </p>

            {/* Action buttons */}
            <div className="flex gap-2">
                <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTogglePin(note)}
                    className="h-7 px-2 text-xs"
                    title={note.pinned ? 'Unpin note' : 'Pin note'}
                >
                    {note.pinned ? (
                        <PinOff className="h-3 w-3" />
                    ) : (
                        <Pin className="h-3 w-3" />
                    )}
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEditNote(note)}
                    className="h-7 px-2 text-xs"
                    title="Edit note"
                >
                    <Edit2 className="h-3 w-3" />
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteNote(note.id)}
                    className="h-7 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                    title="Delete note"
                >
                    <Trash2 className="h-3 w-3" />
                </Button>
            </div>
        </div>
    );

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <StickyNote className="h-5 w-5" />
                        Research Notes
                    </DialogTitle>
                    <DialogDescription>
                        Create and manage your research notes and reminders
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto px-1">
                    {/* Create/Edit Form */}
                    {(isCreating || editingNote) && (
                        <div className="mb-6 p-4 border-2 border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                            <h3 className="font-semibold text-sm mb-3">
                                {editingNote ? 'Edit Note' : 'Create New Note'}
                            </h3>

                            <div className="space-y-3">
                                <div>
                                    <label className="block text-xs font-medium mb-1">
                                        Title *
                                    </label>
                                    <Input
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="Enter note title..."
                                        className="w-full"
                                        maxLength={200}
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-medium mb-1">
                                        Content
                                    </label>
                                    <Textarea
                                        value={content}
                                        onChange={(e) => setContent(e.target.value)}
                                        placeholder="Write your note..."
                                        rows={4}
                                        className="w-full resize-none"
                                        maxLength={10000}
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-medium mb-2">
                                        Color
                                    </label>
                                    <div className="flex gap-2">
                                        {NOTE_COLORS.map((color) => (
                                            <button
                                                key={color.value}
                                                type="button"
                                                onClick={() => setSelectedColor(color.value)}
                                                className={`w-8 h-8 rounded-full border-2 transition-all ${
                                                    selectedColor === color.value
                                                        ? 'border-blue-600 scale-110'
                                                        : 'border-gray-300 hover:scale-105'
                                                }`}
                                                style={{ backgroundColor: color.value }}
                                                title={color.name}
                                            />
                                        ))}
                                    </div>
                                </div>

                                <div className="flex gap-2 pt-2">
                                    <Button
                                        type="button"
                                        onClick={handleSaveNote}
                                        size="sm"
                                        className="flex-1"
                                    >
                                        <Save className="h-3 w-3 mr-1" />
                                        Save Note
                                    </Button>
                                    <Button
                                        type="button"
                                        onClick={handleCancelEdit}
                                        size="sm"
                                        variant="outline"
                                    >
                                        <X className="h-3 w-3 mr-1" />
                                        Cancel
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Create New Button */}
                    {!isCreating && !editingNote && (
                        <Button
                            type="button"
                            onClick={handleCreateNew}
                            className="w-full mb-4"
                            variant="outline"
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Create New Note
                        </Button>
                    )}

                    {/* Notes Grid */}
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                        </div>
                    ) : notes.length === 0 ? (
                        <div className="text-center py-12">
                            <StickyNote className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                            <p className="text-gray-500">No notes yet. Create your first note!</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {notes.map(renderNoteCard)}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
