/**
 * Editor Utility Functions
 * Helper functions for TipTap editor and content conversion
 */

/**
 * Convert TipTap JSON to backend API format
 * Supports both paragraphs and headings (APA 7th Edition levels 1-5)
 * 
 * @param {Object} editorJSON - TipTap editor content as JSON
 * @returns {Object} - Formatted content for backend with content array and citedPapers
 */
export function convertEditorToAPIFormat(editorJSON) {
    const content = [];
    const citedPapers = new Set();

    if (!editorJSON?.content) {
        return { content: [], citedPapers: [] };
    }

    // Iterate through editor content
    editorJSON.content.forEach((node) => {
        // Handle heading nodes
        if (node.type === 'heading') {
            const level = node.attrs?.level || 1;
            let headingText = '';
            
            // Extract text from heading content
            if (node.content) {
                node.content.forEach((contentNode) => {
                    if (contentNode.type === 'text') {
                        headingText += contentNode.text;
                    }
                });
            }
            
            // Only add non-empty headings
            if (headingText.trim()) {
                content.push({
                    type: 'heading',
                    level: level,
                    text: headingText.trim()
                });
            }
        }
        // Handle paragraph nodes
        else if (node.type === 'paragraph') {
            let text = '';
            const citations = [];

            // Process paragraph content
            if (node.content) {
                node.content.forEach((contentNode) => {
                    if (contentNode.type === 'text') {
                        text += contentNode.text;
                    } else if (contentNode.type === 'mention') {
                        // Convert mention to citation placeholder
                        const paperId = contentNode.attrs?.id;
                        if (paperId) {
                            text += `{{${paperId}}}`;
                            citations.push(paperId);
                            citedPapers.add(paperId);
                        }
                    }
                });
            }

            // Only add non-empty paragraphs
            if (text.trim()) {
                content.push({
                    type: 'paragraph',
                    text: text,
                    citations: citations
                });
            }
        }
    });

    return {
        content: content,
        citedPapers: Array.from(citedPapers)
    };
}

/**
 * Extract paper metadata for cited papers
 * @param {Array} citedPaperIds - List of paper IDs
 * @param {Array} availablePapers - All available papers with metadata
 * @returns {Object} - Map of paper_id to metadata
 */
export function extractReferencesMetadata(citedPaperIds, availablePapers) {
    const metadata = {};

    citedPaperIds.forEach(paperId => {
        const paper = availablePapers.find(p => p.id === paperId);
        if (paper) {
            metadata[paperId] = {
                title: paper.title || 'Untitled',
                author_list: paper.authors || [],
                year: paper.publication_year?.toString() || paper.year?.toString() || 'n.d.',
                doi: paper.doi || null,
                publisher: paper.journal_or_conference || paper.publisher || paper.journal || null,
                volume: paper.volume || null,
                issue: paper.issue || null,
                pages: paper.pages || null,
                publication_type: paper.publication_type || 'journal'
            };
        }
    });

    return metadata;
}

/**
 * Format author name for display in citation chip
 * @param {Array} authors - List of author names
 * @returns {string} - Formatted author string (e.g., "Smith et al.")
 */
export function formatAuthorsForDisplay(authors) {
    if (!authors || authors.length === 0) return 'Unknown';
    
    const getLastName = (author) => {
        if (author.includes(',')) {
            return author.split(',')[0].trim();
        }
        const parts = author.trim().split(' ');
        return parts[parts.length - 1];
    };

    if (authors.length === 1) {
        return getLastName(authors[0]);
    } else if (authors.length === 2) {
        return `${getLastName(authors[0])} & ${getLastName(authors[1])}`;
    } else {
        return `${getLastName(authors[0])} et al.`;
    }
}

/**
 * Sanitize filename for download
 * @param {string} title - Document title
 * @returns {string} - Safe filename
 */
export function sanitizeFilename(title) {
    return title
        .replace(/[^a-z0-9\s-]/gi, '')
        .trim()
        .replace(/\s+/g, '_')
        .substring(0, 50);
}