/**
 * Editor Menu Bar (Toolbar)
 * Formatting controls for the TipTap editor
 */

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
    Bold,
    Italic,
    List,
    ListOrdered,
    Heading2,
    Undo,
    Redo,
    Quote,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Toolbar button component (defined outside to avoid recreation on each render)
const ToolbarButton = ({ onClick, isActive, children, title }) => (
    <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={onClick}
        className={cn(
            'h-8 w-8',
            isActive && 'bg-gray-200 dark:bg-gray-700'
        )}
        title={title}
    >
        {children}
    </Button>
);

export default function EditorMenuBar({ editor }) {
    if (!editor) return null;

    return (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-2 flex items-center gap-1 flex-wrap sticky top-0 z-10">
            {/* Undo/Redo */}
            <ToolbarButton
                onClick={() => editor.chain().focus().undo().run()}
                title="Undo (Ctrl+Z)"
                isActive={false}
            >
                <Undo className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().redo().run()}
                title="Redo (Ctrl+Y)"
                isActive={false}
            >
                <Redo className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Text Formatting */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBold().run()}
                isActive={editor.isActive('bold')}
                title="Bold (Ctrl+B)"
            >
                <Bold className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleItalic().run()}
                isActive={editor.isActive('italic')}
                title="Italic (Ctrl+I)"
            >
                <Italic className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Headings */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                isActive={editor.isActive('heading', { level: 2 })}
                title="Heading"
            >
                <Heading2 className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Lists */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                isActive={editor.isActive('bulletList')}
                title="Bullet List"
            >
                <List className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                isActive={editor.isActive('orderedList')}
                title="Numbered List"
            >
                <ListOrdered className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Quote */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                isActive={editor.isActive('blockquote')}
                title="Block Quote"
            >
                <Quote className="h-4 w-4" />
            </ToolbarButton>

            <div className="ml-auto text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
                Type <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-mono">@</kbd> to cite a paper
            </div>
        </div>
    );
}