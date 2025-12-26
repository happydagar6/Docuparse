/**
 * Editor Utility Functions
 * Helper functions for TipTap editor and content conversion
 */

/**
 * Convert TipTap JSON to backend API format
 * Supports paragraphs, headings, tables, and figures (APA 7th Edition)
 * 
 * @param {Object} editorJSON - TipTap editor content as JSON
 * @returns {Object} - Formatted content for backend with content array and citedPapers
 */
export function convertEditorToAPIFormat(editorJSON) {
    const content = [];
    const citedPapers = new Set();
    
    // Track table and figure numbers for sequential numbering
    let tableNumber = 1;
    let figureNumber = 1;

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
        // Handle table nodes
        else if (node.type === 'table') {
            const tableData = extractTableData(node);
            if (tableData.rows.length > 0) {
                content.push({
                    type: 'table',
                    number: tableNumber++,
                    title: tableData.title || `Table ${tableNumber - 1}`,
                    rows: tableData.rows,
                    header_rows: tableData.headerRows || 1,
                    note: tableData.note || null
                });
            }
        }
        // Handle image nodes (figures)
        else if (node.type === 'image') {
            const imageData = extractImageData(node, figureNumber);
            if (imageData) {
                content.push({
                    type: 'figure',
                    number: figureNumber++,
                    file_id: imageData.file_id,
                    filename: imageData.filename,
                    caption: imageData.caption,
                    alt_text: imageData.alt_text,
                    width_percent: imageData.width_percent
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
 * Extract table data from TipTap table node
 * 
 * @param {Object} tableNode - TipTap table node
 * @returns {Object} - Table data with rows, title, and header info
 */
function extractTableData(tableNode) {
    const rows = [];
    let headerRows = 0;
    
    // Iterate through table rows
    if (tableNode.content) {
        tableNode.content.forEach((rowNode) => {
            if (rowNode.type === 'tableRow') {
                const row = [];
                let isHeaderRow = false;
                
                // Iterate through cells in the row
                if (rowNode.content) {
                    rowNode.content.forEach((cellNode) => {
                        let cellText = '';
                        
                        // Check if this is a header cell
                        if (cellNode.type === 'tableHeader') {
                            isHeaderRow = true;
                        }
                        
                        // Extract cell content
                        if (cellNode.content) {
                            cellNode.content.forEach((para) => {
                                if (para.content) {
                                    para.content.forEach((textNode) => {
                                        if (textNode.type === 'text') {
                                            cellText += textNode.text;
                                        }
                                    });
                                }
                            });
                        }
                        
                        row.push(cellText);
                    });
                }
                
                if (isHeaderRow) {
                    headerRows++;
                }
                
                rows.push(row);
            }
        });
    }
    
    return {
        rows,
        headerRows: headerRows || 1,
        title: '', // Can be enhanced to extract title from attributes
        note: null // Can be enhanced to extract notes from attributes
    };
}

/**
 * Extract image/figure data from TipTap image node
 * 
 * @param {Object} imageNode - TipTap image node
 * @param {number} figureNumber - Current figure number
 * @returns {Object|null} - Figure data or null if invalid
 */
function extractImageData(imageNode, figureNumber) {
    const attrs = imageNode.attrs || {};
    
    // Extract custom data attributes (stored when image was uploaded)
    const file_id = attrs['data-file-id'] || attrs.src?.split('/').pop()?.split('.')[0] || '';
    const filename = attrs['data-filename'] || attrs.src?.split('/').pop() || 'image.png';
    const caption = attrs['data-caption'] || attrs.title || `Figure ${figureNumber}`;
    const alt_text = attrs['data-alt-text'] || attrs.alt || caption;
    const width_percent = parseInt(attrs['data-width-percent']) || 100;
    
    // Validate that we have at least a file_id or src
    if (!file_id && !attrs.src) {
        return null;
    }
    
    return {
        file_id,
        filename,
        caption,
        alt_text,
        width_percent
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