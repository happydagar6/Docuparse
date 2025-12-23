/**
 * Editor Utility Functions
 * Helper functions for TipTap editor and content conversion
 */

/**
 * Convert TipTap JSON to backend API format
 * @param {Object} editorJSON - TipTap editor content as JSON
 * @returns {Object} - Formatted content for backend
 */
export function convertEditorToAPIFormat(editorJSON) {
    const paragraphs = [];
    const citedPapers = new Set();

    if (!editorJSON?.content) {
        return { content: [], citedPapers: [] };
    }

    // Iterate through editor content
    editorJSON.content.forEach((node) => {
        if (node.type === 'paragraph') {
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
                paragraphs.push({
                    text: text,
                    citations: citations
                });
            }
        }
    });

    return {
        content: paragraphs,
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
                year: paper.year?.toString() || 'n.d.',
                doi: paper.doi || null,
                publisher: paper.publisher || paper.journal || null
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