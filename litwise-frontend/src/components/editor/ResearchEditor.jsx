'use client';

/**
 * Research Editor Component
 * TipTap-based editor with smart citation autocomplete and APA 7th Edition support
 * 
 * Features:
 * - Smart citation system: Type @ to search and cite papers from your library
 * - Multi-level headings: 5 APA heading levels with proper formatting
 * - Rich text editing: Bold, italic, lists, blockquotes
 * - Abstract & Keywords: Dedicated fields with word count validation
 * - APA Export: Generate properly formatted Word documents (.docx)
 * 
 * APA 7th Edition Heading Levels:
 * - Level 1: Centered, Bold (e.g., Method, Results, Discussion)
 * - Level 2: Left-Aligned, Bold (e.g., Participants, Materials)
 * - Level 3: Left-Aligned, Bold Italic (e.g., Subsection titles)
 * - Level 4: Indented, Bold, Run-in (text continues on same line)
 * - Level 5: Indented, Bold Italic, Run-in (text continues on same line)
 * 
 * Keyboard Shortcuts:
 * - Ctrl+B: Bold
 * - Ctrl+I: Italic
 * - Ctrl+Z: Undo
 * - Ctrl+Y: Redo
 * - Ctrl+Shift+1-5: Heading levels 1-5
 * - @: Trigger citation autocomplete
 */

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Mention from '@tiptap/extension-mention';
import Placeholder from '@tiptap/extension-placeholder';
import Typography from '@tiptap/extension-typography';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { Image } from '@tiptap/extension-image';
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Download, Loader2, AlertCircle } from 'lucide-react';
import EditorMenuBar from './EditorMenuBar';
import ImageUploadModal from './ImageUploadModal';
import { convertEditorToAPIFormat, extractReferencesMetadata, sanitizeFilename, formatAuthorsForDisplay } from '@/lib/editor-utils';
import { exportAPADocument } from '@/lib/api';
import { toast } from 'sonner';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';

// Citation suggestion wrapper class for TipTap
class CitationSuggestionWrapper {
    constructor(props) {
        this.props = props;
        this.element = null;
        this.selectedIndex = 0;
        this.render();
    }

    render() {
        const div = document.createElement('div');
        div.className = 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden max-h-80 overflow-y-auto';
        
        if (!this.props.items || this.props.items.length === 0) {
            div.innerHTML = '<div class="p-3 text-sm text-gray-500 dark:text-gray-400">No papers found</div>';
        } else {
            // Clear previous content
            div.innerHTML = '';
            
            this.props.items.forEach((item, index) => {
                // Safely extract and format authors
                let authorDisplay = 'Unknown Author';
                if (item.authors && item.authors.length > 0) {
                    const getLastName = (author) => {
                        if (typeof author === 'object' && author.name) {
                            author = author.name;
                        }
                        if (typeof author !== 'string') return 'Unknown';
                        if (author.includes(',')) {
                            return author.split(',')[0].trim();
                        }
                        const parts = author.trim().split(' ');
                        return parts[parts.length - 1] || 'Unknown';
                    };
                    
                    const lastNames = item.authors.map(getLastName);
                    if (lastNames.length === 1) {
                        authorDisplay = lastNames[0];
                    } else if (lastNames.length === 2) {
                        authorDisplay = `${lastNames[0]} & ${lastNames[1]}`;
                    } else if (lastNames.length > 2) {
                        authorDisplay = `${lastNames[0]} et al.`;
                    }
                }
                
                const year = item.year || item.publication_year || 'n.d.';
                
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'w-full text-left px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0 focus:outline-none';
                
                if (index === 0) {
                    button.classList.add('bg-blue-50', 'dark:bg-blue-900/20');
                }

                button.innerHTML = `
                    <div class="font-medium text-gray-900 dark:text-gray-100 text-sm line-clamp-1">${item.title || 'Untitled'}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">${authorDisplay} • ${year}</div>
                `;

                button.onclick = () => this.selectItem(index);
                button.dataset.index = index;
                div.appendChild(button);
            });
        }

        this.element = div;
    }

    selectItem(index) {
        const validIndex = Math.min(Math.max(0, index), this.props.items.length - 1);
        const item = this.props.items[validIndex];
        if (item) {
            this.props.command({
                id: item.id,
                label: item.title || 'Untitled',
                authors: item.authors || [],
                year: item.year || item.publication_year || 'n.d.'
            });
        }
    }

    onKeyDown(event) {
        if (event.event.key === 'ArrowUp') {
            this.selectedIndex = (this.selectedIndex + this.props.items.length - 1) % this.props.items.length;
            this.updateSelection();
            return true;
        }

        if (event.event.key === 'ArrowDown') {
            this.selectedIndex = (this.selectedIndex + 1) % this.props.items.length;
            this.updateSelection();
            return true;
        }

        if (event.event.key === 'Enter') {
            this.selectItem(this.selectedIndex);
            return true;
        }

        return false;
    }

    updateSelection() {
        const buttons = this.element.querySelectorAll('button');
        buttons.forEach((btn, index) => {
            if (index === this.selectedIndex) {
                btn.classList.add('bg-blue-50', 'dark:bg-blue-900/20');
            } else {
                btn.classList.remove('bg-blue-50', 'dark:bg-blue-900/20');
            }
        });
    }

    update(props) {
        this.props = props;
        this.selectedIndex = 0;
        this.render();
    }

    destroy() {
        if (this.element) {
            this.element.remove();
        }
    }
}

export default function ResearchEditor({ availablePapers = [] }) {
    const [documentTitle, setDocumentTitle] = useState('');
    const [runningHead, setRunningHead] = useState('');
    const [authors, setAuthors] = useState(['']);
    const [affiliation, setAffiliation] = useState('Independent Researcher');
    const [abstract, setAbstract] = useState('');
    const [keywords, setKeywords] = useState('');
    const [isExporting, setIsExporting] = useState(false);
    const [isImageModalOpen, setIsImageModalOpen] = useState(false);
    const [figureNumber, setFigureNumber] = useState(1);

    // Calculate word count for abstract
    const abstractWordCount = abstract.trim() ? abstract.trim().split(/\s+/).length : 0;
    const isAbstractTooLong = abstractWordCount > 250;

    // Configure TipTap editor
    const editor = useEditor({
        immediatelyRender: false, // Required for Next.js SSR
        extensions: [
            StarterKit.configure({
                heading: {
                    levels: [1, 2, 3, 4, 5], // APA 7th Edition supports 5 heading levels
                },
            }),
            Typography,
            // Table extensions for APA tables
            Table.configure({
                resizable: true,
                HTMLAttributes: {
                    class: 'editor-table',
                },
            }),
            TableRow,
            TableCell,
            TableHeader,
            // Image extension for APA figures
            Image.configure({
                inline: false,
                allowBase64: false,
                HTMLAttributes: {
                    class: 'editor-image',
                },
            }),
            Placeholder.configure({
                placeholder: 'Start writing your research paper... Type @ to cite a paper from your library.',
            }),
            Mention.configure({
                HTMLAttributes: {
                    class: 'citation-mention',
                },
                suggestion: {
                    items: ({ query }) => {
                        return availablePapers
                            .filter(paper =>
                                paper.title?.toLowerCase().includes(query.toLowerCase()) ||
                                paper.authors?.some(author =>
                                    author.toLowerCase().includes(query.toLowerCase())
                                )
                            )
                            .slice(0, 10);
                    },
                    render: () => {
                        let component;
                        let popup;

                        return {
                            onStart: (props) => {
                                component = new CitationSuggestionWrapper(props);

                                if (!props.clientRect) {
                                    return;
                                }

                                popup = tippy('body', {
                                    getReferenceClientRect: props.clientRect,
                                    appendTo: () => document.body,
                                    content: component.element,
                                    showOnCreate: true,
                                    interactive: true,
                                    trigger: 'manual',
                                    placement: 'bottom-start',
                                });
                            },

                            onUpdate(props) {
                                component?.update(props);

                                if (!props.clientRect) {
                                    return;
                                }

                                popup?.[0]?.setProps({
                                    getReferenceClientRect: props.clientRect,
                                });
                            },

                            onKeyDown(props) {
                                if (props.event.key === 'Escape') {
                                    popup?.[0]?.hide();
                                    return true;
                                }

                                return component?.onKeyDown(props);
                            },

                            onExit() {
                                popup?.[0]?.destroy();
                                component?.destroy();
                            },
                        };
                    },
                },
                renderHTML({ options, node }) {
                    const paper = availablePapers.find(p => p.id === node.attrs.id);
                    return [
                        'span',
                        {
                            class: 'citation-chip',
                            'data-id': node.attrs.id,
                        },
                        `(${node.attrs.label})`,
                    ];
                },
            }),
        ],
        content: '',
        editorProps: {
            attributes: {
                class: 'prose prose-sm sm:prose lg:prose-lg dark:prose-invert max-w-none focus:outline-none min-h-[500px] p-8',
            },
        },
    });

    // Listen for image upload button click from toolbar
    React.useEffect(() => {
        const handleOpenImageUpload = () => {
            setIsImageModalOpen(true);
        };

        window.addEventListener('openImageUpload', handleOpenImageUpload);
        
        return () => {
            window.removeEventListener('openImageUpload', handleOpenImageUpload);
        };
    }, []);

    /**
     * Handle image insertion from upload modal
     * Stores metadata in editor as custom node attributes
     * 
     * @param {Object} imageData - Uploaded image data from modal
     */
    const handleImageInsert = (imageData) => {
        if (!editor) return;

        // Insert custom figure node with metadata
        // The image will be rendered with figure number and caption
        editor
            .chain()
            .focus()
            .setImage({
                src: imageData.url,
                alt: imageData.alt_text,
                title: imageData.caption,
                // Store custom attributes for APA export
                'data-figure-number': figureNumber,
                'data-file-id': imageData.file_id,
                'data-filename': imageData.filename,
                'data-caption': imageData.caption,
                'data-width-percent': imageData.width_percent,
            })
            .run();

        // Increment figure number for next insertion
        setFigureNumber(prev => prev + 1);

        toast.success(`Figure ${figureNumber} inserted`);
    };

    // Handle author input
    const handleAuthorChange = (index, value) => {
        const newAuthors = [...authors];
        newAuthors[index] = value;
        setAuthors(newAuthors);
    };

    const addAuthor = () => {
        setAuthors([...authors, '']);
    };

    const removeAuthor = (index) => {
        if (authors.length > 1) {
            setAuthors(authors.filter((_, i) => i !== index));
        }
    };

    // Export to Word
    const handleExport = async () => {
        // Validation
        if (!documentTitle.trim()) {
            toast.error('Please enter a document title');
            return;
        }

        if (!runningHead.trim()) {
            toast.error('Please enter a running head');
            return;
        }

        if (authors.length === 0 || !authors[0].trim()) {
            toast.error('Please enter at least one author');
            return;
        }

        // Validate abstract word count
        if (isAbstractTooLong) {
            toast.error('Abstract is too long. Please reduce to 250 words or less.');
            return;
        }

        if (!editor) {
            toast.error('Editor not initialized');
            return;
        }

        setIsExporting(true);

        try {
            // Convert editor content to API format
            const editorJSON = editor.getJSON();
            
            // Check if editor has any text content
            const editorText = editor.getText().trim();
            if (!editorText) {
                toast.error('Please write some content before exporting');
                setIsExporting(false);
                return;
            }
            
            const { content, citedPapers } = convertEditorToAPIFormat(editorJSON);

            if (content.length === 0) {
                toast.error('Please write some content before exporting');
                setIsExporting(false);
                return;
            }

            // Extract metadata for cited papers
            const referencesMetadata = extractReferencesMetadata(citedPapers, availablePapers);

            // Prepare request
            const requestData = {
                title: documentTitle,
                running_head: runningHead.substring(0, 50),
                authors: authors.filter(a => a.trim()),
                affiliation: affiliation,
                abstract: abstract.trim() || null,
                keywords: keywords.trim() ? keywords.split(',').map(k => k.trim()).filter(k => k) : [],
                content: content,
                references_metadata: referencesMetadata,
            };

            // Call API
            const blob = await exportAPADocument(requestData);

            // Download file
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${sanitizeFilename(documentTitle)}.docx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast.success('Document exported successfully!');
        } catch (error) {
            console.error('Export error:', error);
            toast.error(error.message || 'Failed to export document');
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Document Metadata Section */}
            <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-4 md:p-6 overflow-y-auto shrink-0 max-h-[45vh]">
                <div className="max-w-4xl mx-auto space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Document Title *
                        </label>
                        <Input
                            type="text"
                            value={documentTitle}
                            onChange={(e) => setDocumentTitle(e.target.value)}
                            placeholder="The Impact of Machine Learning on Healthcare"
                            className="w-full"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Running Head * <span className="text-xs text-gray-500">(Max 50 chars)</span>
                            </label>
                            <Input
                                type="text"
                                value={runningHead}
                                onChange={(e) => setRunningHead(e.target.value.substring(0, 50))}
                                placeholder="ML IN HEALTHCARE"
                                className="w-full uppercase"
                                maxLength={50}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Affiliation
                            </label>
                            <Input
                                type="text"
                                value={affiliation}
                                onChange={(e) => setAffiliation(e.target.value)}
                                placeholder="Stanford University"
                                className="w-full"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Authors *
                        </label>
                        <div className="space-y-2">
                            {authors.map((author, index) => (
                                <div key={index} className="flex gap-2">
                                    <Input
                                        type="text"
                                        value={author}
                                        onChange={(e) => handleAuthorChange(index, e.target.value)}
                                        placeholder={`Author ${index + 1}`}
                                        className="flex-1"
                                    />
                                    {authors.length > 1 && (
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="icon"
                                            onClick={() => removeAuthor(index)}
                                        >
                                            ×
                                        </Button>
                                    )}
                                </div>
                            ))}
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={addAuthor}
                            >
                                + Add Author
                            </Button>
                        </div>
                    </div>

                    {/* Abstract Field (Optional but recommended for APA) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Abstract <span className="text-xs text-gray-500">(Optional, max 250 words)</span>
                        </label>
                        <Textarea
                            value={abstract}
                            onChange={(e) => setAbstract(e.target.value)}
                            placeholder="Provide a brief summary of your research (recommended for professional papers and theses)..."
                            className={`w-full min-h-[100px] resize-y ${isAbstractTooLong ? 'border-red-500 focus:border-red-500' : ''}`}
                            rows={4}
                        />
                        <div className="flex justify-between items-center mt-1">
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                A concise summary appears on Page 2 of your APA document
                            </p>
                            <p className={`text-xs font-medium ${isAbstractTooLong ? 'text-red-600 dark:text-red-400' : abstractWordCount > 200 ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-500 dark:text-gray-400'}`}>
                                {abstractWordCount}/250 words
                            </p>
                        </div>
                    </div>

                    {/* Keywords Field (Optional but recommended) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Keywords <span className="text-xs text-gray-500">(Optional, 3-5 recommended)</span>
                        </label>
                        <Input
                            type="text"
                            value={keywords}
                            onChange={(e) => setKeywords(e.target.value)}
                            placeholder="machine learning, healthcare, artificial intelligence"
                            className="w-full"
                        />
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Separate keywords with commas. Appears below abstract for indexing.
                        </p>
                    </div>
                </div>
            </div>

            {/* Editor Section */}
            <div className="flex-1 overflow-hidden flex flex-col bg-gray-50 dark:bg-gray-900">
                <EditorMenuBar editor={editor} />

                <div className="flex-1 overflow-y-auto">
                    {/* Info Banner - Inline at top of editor if no papers */}
                    {availablePapers.length === 0 && (
                        <div className="max-w-4xl mx-auto mt-4 px-4">
                            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4 shadow-sm">
                                <div className="flex items-start gap-3">
                                    <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="font-medium text-yellow-800 dark:text-yellow-200 text-sm">
                                            No papers in library
                                        </h4>
                                        <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                                            Upload papers to your library to enable citation autocomplete. Type <kbd className="px-1.5 py-0.5 bg-yellow-200 dark:bg-yellow-800 rounded text-xs font-mono">@</kbd> in the editor to cite papers.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="max-w-4xl mx-auto my-8 px-4 pb-8">
                        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg min-h-[600px]">
                            <EditorContent editor={editor} />
                        </div>
                    </div>
                </div>

                {/* Editor Footer with Export Button */}
                <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 md:px-6 py-4 shrink-0">
                    <div className="max-w-4xl mx-auto flex justify-end">
                        <Button
                            onClick={handleExport}
                            disabled={isExporting}
                            size="lg"
                            className="shadow-lg bg-blue-600 hover:bg-blue-700 text-white"
                        >
                            {isExporting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 md:h-5 md:w-5 animate-spin" />
                                    <span className="hidden sm:inline">Exporting...</span>
                                    <span className="sm:hidden">Export</span>
                                </>
                            ) : (
                                <>
                                    <Download className="mr-2 h-4 w-4 md:h-5 md:w-5" />
                                    <span className="hidden sm:inline">Export to Word (APA)</span>
                                    <span className="sm:hidden">Export</span>
                                </>
                            )}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Image Upload Modal */}
            <ImageUploadModal
                isOpen={isImageModalOpen}
                onClose={() => setIsImageModalOpen(false)}
                onImageInsert={handleImageInsert}
            />
        </div>
    );
}