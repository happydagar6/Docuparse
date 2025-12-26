/**
 * Editor Menu Bar (Toolbar)
 * Formatting controls for the TipTap editor with APA 7th Edition heading support
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
    Bold,
    Italic,
    List,
    ListOrdered,
    Heading1,
    Heading2,
    Heading3,
    Undo,
    Redo,
    Quote,
    ChevronDown,
    Type,
    Table2,
    ImagePlus,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Toolbar button component (defined outside to avoid recreation on each render)
const ToolbarButton = ({ onClick, isActive, children, title, disabled }) => (
    <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={onClick}
        disabled={disabled}
        className={cn(
            'h-8 w-8',
            isActive && 'bg-gray-200 dark:bg-gray-700'
        )}
        title={title}
    >
        {children}
    </Button>
);

// Heading dropdown menu component
const HeadingDropdown = ({ editor }) => {
    const [isOpen, setIsOpen] = useState(false);
    
    // Get current active heading level
    const getActiveHeading = () => {
        for (let level = 1; level <= 5; level++) {
            if (editor.isActive('heading', { level })) {
                return level;
            }
        }
        return null;
    };
    
    const activeLevel = getActiveHeading();
    
    // APA 7th Edition heading descriptions
    const headings = [
        { level: 1, label: 'Heading 1', description: 'Centered, Bold', icon: Heading1 },
        { level: 2, label: 'Heading 2', description: 'Left-Aligned, Bold', icon: Heading2 },
        { level: 3, label: 'Heading 3', description: 'Left-Aligned, Bold Italic', icon: Heading3 },
        { level: 4, label: 'Heading 4', description: 'Indented, Bold, Run-in', icon: Type },
        { level: 5, label: 'Heading 5', description: 'Indented, Bold Italic, Run-in', icon: Type },
    ];
    
    const setHeading = (level) => {
        editor.chain().focus().toggleHeading({ level }).run();
        setIsOpen(false);
    };
    
    const setParagraph = () => {
        editor.chain().focus().setParagraph().run();
        setIsOpen(false);
    };
    
    return (
        <div className="relative">
            <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    'h-8 px-2 text-xs font-medium min-w-[100px] justify-between',
                    activeLevel && 'bg-gray-200 dark:bg-gray-700'
                )}
                title="Text formatting styles"
            >
                <span className="flex items-center gap-1.5">
                    {activeLevel ? (
                        <>
                            {React.createElement(headings[activeLevel - 1].icon, { className: 'h-3.5 w-3.5' })}
                            Level {activeLevel}
                        </>
                    ) : (
                        <>
                            <Type className="h-3.5 w-3.5" />
                            Normal
                        </>
                    )}
                </span>
                <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
            
            {isOpen && (
                <>
                    {/* Backdrop to close dropdown */}
                    <div 
                        className="fixed inset-0 z-20" 
                        onClick={() => setIsOpen(false)}
                    />
                    
                    {/* Dropdown menu */}
                    <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-30 min-w-[280px] py-1">
                        {/* Normal text option */}
                        <button
                            type="button"
                            onClick={setParagraph}
                            className={cn(
                                'w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-start gap-3 transition-colors',
                                !activeLevel && 'bg-blue-50 dark:bg-blue-900/20'
                            )}
                        >
                            <Type className="h-4 w-4 mt-0.5 shrink-0 text-gray-600 dark:text-gray-400" />
                            <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                    Normal Text
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                    Body paragraph
                                </div>
                            </div>
                        </button>
                        
                        <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                        
                        {/* Heading options */}
                        {headings.map(({ level, label, description, icon: Icon }) => (
                            <button
                                key={level}
                                type="button"
                                onClick={() => setHeading(level)}
                                className={cn(
                                    'w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-start gap-3 transition-colors',
                                    activeLevel === level && 'bg-blue-50 dark:bg-blue-900/20'
                                )}
                            >
                                <Icon className="h-4 w-4 mt-0.5 shrink-0 text-gray-600 dark:text-gray-400" />
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {label}
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        {description}
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default function EditorMenuBar({ editor }) {
    if (!editor) return null;

    return (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-2 flex items-center gap-1 flex-wrap sticky top-0 z-10">
            {/* Undo/Redo */}
            <ToolbarButton
                onClick={() => editor.chain().focus().undo().run()}
                title="Undo (Ctrl+Z)"
                isActive={false}
                disabled={!editor.can().undo()}
            >
                <Undo className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
                onClick={() => editor.chain().focus().redo().run()}
                title="Redo (Ctrl+Y)"
                isActive={false}
                disabled={!editor.can().redo()}
            >
                <Redo className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Heading Dropdown - APA 7th Edition Levels 1-5 */}
            <HeadingDropdown editor={editor} />

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

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Table */}
            <ToolbarButton
                onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
                isActive={editor.isActive('table')}
                title="Insert Table (3x3)"
            >
                <Table2 className="h-4 w-4" />
            </ToolbarButton>

            {/* Image - Will open upload modal */}
            <ToolbarButton
                onClick={() => {
                    // Trigger custom image upload event
                    const event = new CustomEvent('openImageUpload');
                    window.dispatchEvent(event);
                }}
                isActive={false}
                title="Insert Figure (Upload Image)"
            >
                <ImagePlus className="h-4 w-4" />
            </ToolbarButton>

            <div className="ml-auto text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
                Type <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-mono">@</kbd> to cite a paper
            </div>
        </div>
    );
}