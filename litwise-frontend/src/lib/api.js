/**
 * API Integration Layer for Litwise Backend
 * 
 * This file centralizes all API calls to the FastAPI backend.
 * It handles:
 * - HTTP requests with proper error handling
 * - Response formatting
 * - Environment configuration
 * - Request/response interceptors
 * - JWT authentication
 */

import { getSupabaseClient } from './supabase/client';

// API base configuration

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Get the current JWT token from Supabase session
 * @returns {Promise<string|null>} - JWT access token or null if not authenticated
 */
async function getAuthToken() {
    try {
        const supabase = getSupabaseClient();
        const { data: { session } } = await supabase.auth.getSession();
        return session?.access_token || null;
    } catch (error) {
        console.error('Error getting auth token:', error);
        return null;
    }
}

/**
 * Generic API request handler with authentication
 * @param {string} endpoint - API endpoint path
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise} - API response data
 */

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Get auth token
    const token = await getAuthToken();
    
    // Build headers
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    // Add Authorization header if token exists
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            headers,
            ...options,
        });

        // Handle HTTP errors
        if(!response.ok){
            const errorData = await response.json().catch(() => ({
                detail: `HTTP ${response.status}: ${response.statusText}`
            }));
            throw new Error(errorData.detail || errorData.message || 'API request failed');
        }
        return await response.json(); // Return parsed JSON response
    } catch (error){
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}


/**
 * Upload PDF file to backend (without AI processing)
 * 
 * Flow:
 * 1. Create FormData with PDF file
 * 2. POST to /upload endpoint
 * 3. Backend extracts text → stores in Supabase/Qdrant
 * 4. Returns paper metadata (without AI summary)
 * 
 * @param {File} file - PDF file to upload
 * @param {function} onProgress - Progress callback (optional)
 * @returns {Promise<object>} - Upload result with paper data
 */

export async function uploadPaper(file, onProgress){
    const formData = new FormData(); // Create FormData
    formData.append('file', file); // Append PDF file
    
    // Extract clean title from filename (remove extension and clean up)
    let title = '';
    if (file.name) {
        // Remove .pdf extension
        title = file.name.replace(/\.pdf$/i, '');
        // Replace underscores and hyphens with spaces
        title = title.replace(/[_-]/g, ' ');
        // Clean up extra spaces
        title = title.replace(/\s+/g, ' ').trim();
        // Capitalize first letter of each word
        title = title.replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // Only append title if we have one
    if (title) {
        formData.append('title', title);
    }

    try {
        // Get auth token
        const token = await getAuthToken();
        
        // Build headers
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: "POST",
            headers,
            body: formData,
            // Note: Don't set Content-Type header for FormData, browser sets it automatically
        });

        if(!response.ok){
            const errorData = await response.json().catch(() => ({
                detail: `Upload failed: ${response.statusText}`
            }));
            throw new Error(errorData.detail || 'Upload failed');
        }
        return await response.json();
    } catch (error) {
        console.error("Upload Error:", error);
        throw error;
    }
};

/**
 * Generate AI summary for an uploaded paper
 * 
 * @param {string} paperId - Paper UUID
 * @returns {Promise<object>} - Processing result with AI summary
 */
export async function processPaperAI(paperId) {
    return apiRequest(`/papers/${paperId}/process`, {
        method: 'POST',
    });
}

/**
 * Search papers using semantic search
 * 
 * Flow:
 * 1. Send query text to /search endpoint
 * 2. Backend generates embeddings → queries Qdrant → returns relevant papers
 * 3. Results include similarity scores and metadata
 * 
 * @param {string} query - Search query text
 * @param {object} options - Search options
 * @param {object} options.filters - Advanced filters (author, year_from, year_to, keywords)
 * @param {boolean} options.debug - Enable debug mode for detailed response
 * @param {number} options.limit - Maximum results to return (default: 10)
 * @returns {Promise<Array>} - Array of matching papers with scores
 */

export async function searchPapers(query, { filters = null, debug = false, limit = 10 } = {}) {
  const requestBody = { 
    query,
    limit,
    debug 
  };
  
  // Add filters if provided
  if (filters && Object.keys(filters).length > 0) {
    requestBody.filters = filters;
  }
  
  return apiRequest('/search', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
}

/**
 * Get list of all uploaded papers
 * 
 * @returns {Promise<Array>} - Array of paper metadata
 */

export async function getPapers() {
    return apiRequest('/papers');
}


/**
 * Get specific paper details by ID
 * 
 * @param {string} paperId - Paper UUID
 * @returns {Promise<object>} - Paper details with summary
 */

export async function getPaper(paperId){
    return apiRequest(`/papers/${paperId}`);
}

/**
 * Delete paper and its embeddings
 * 
 * @param {string} paperId - Paper UUID
 * @returns {Promise<object>} - Deletion confirmation
 */

export async function deletePaper(paperId){
    return apiRequest(`/papers/${paperId}`, {
        method: 'DELETE'
    });
}

/**
 * Get Qdrant diagnostics (for debugging)
 * 
 * @returns {Promise<object>} - Collection status and sample points
 */

export async function getQdrantDiagnostics(){
    return apiRequest('/qdrant/diagnostics');
}

/**
 * Generate AI-powered synthesis from search results (Phase 1)
 * 
 * Flow:
 * 1. Receives search results from /search endpoint
 * 2. Sends to /search/synthesize endpoint
 * 3. Backend uses LLM (GPT-4) to analyze papers
 * 4. Returns structured synthesis: themes, findings, gaps, trends
 * 
 * @param {string} query - Original search query
 * @param {Array} searchResults - Array of search results from /search
 * @returns {Promise<object>} - Synthesis with themes, findings, gaps, trends
 */
export async function synthesizeSearchResults(query, searchResults, maxPapers = 20) {
    const response = await fetch(`${API_BASE_URL}/search/synthesize`, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query,
            search_results: searchResults,
            max_papers: maxPapers,
        }),
    });
    if(!response.ok){
        const errorData = await response.json().catch(() => {
            return {
                detail: `Synthesis failed: ${response.statusText}`
            }
        })
        throw new Error(errorData.detail || 'Synthesis failed');
    }
    return await response.json();
}

/**
 * Save a synthesis to history
 * 
 * @param {object} synthesis - Synthesis data to save
 * @param {Array} searchResults - Original search results used
 * @param {number} maxPapers - Max papers limit
 * @param {Array} tags - Optional tags for organization
 * @returns {Promise<object>} - Saved synthesis with ID
 */
export async function saveSynthesis(synthesis, searchResults, maxPapers = 20, tags = []) {
    return apiRequest('/synthesis/save', {
        method: 'POST',
        body: JSON.stringify({
            synthesis,
            search_results: searchResults,
            max_papers: maxPapers,
            tags
        }),
    });
}

/**
 * Get synthesis history
 * 
 * @param {number} limit - Number of items to fetch
 * @param {number} offset - Pagination offset
 * @param {string} tag - Optional tag filter
 * @returns {Promise<object>} - History items with pagination info
 */
export async function getSynthesisHistory(limit = 20, offset = 0, tag = null) {
    const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString()
    });
    if (tag) {
        params.append('tag', tag);
    }
    return apiRequest(`/synthesis/history?${params.toString()}`);
}

/**
 * Get specific synthesis by ID
 * 
 * @param {string} synthesisId - UUID of synthesis
 * @returns {Promise<object>} - Full synthesis data
 */
export async function getSynthesisById(synthesisId) {
    return apiRequest(`/synthesis/history/${synthesisId}`);
}

/**
 * Update tags on a saved synthesis
 * 
 * @param {string} synthesisId - UUID of synthesis
 * @param {Array} tags - New tags array
 * @returns {Promise<object>} - Updated synthesis
 */
export async function updateSynthesisTags(synthesisId, tags) {
    return apiRequest(`/synthesis/history/${synthesisId}/tags`, {
        method: 'PATCH',
        body: JSON.stringify({ tags }),
    });
}

/**
 * Delete a saved synthesis
 * 
 * @param {string} synthesisId - UUID of synthesis to delete
 * @returns {Promise<object>} - Deletion confirmation
 */
export async function deleteSynthesis(synthesisId) {
    return apiRequest(`/synthesis/history/${synthesisId}`, {
        method: 'DELETE',
    });
}

/**
 * Utility function to validate file before upload
 * 
 * @param {File} file - File to validate
 * @throws {Error} - If validation fails
 */


export function validatePDFFile(file){
    const maxSize = 35 * 1024 * 1024; // 35MB limit
    const allowedTypes = ['application/pdf'];

    if(!file){
        throw new Error('No file selected');
    }

    if(!allowedTypes.includes(file.type)){
        throw new Error("Please select a valid PDF file");
    }

    if(file.size > maxSize){
        throw new Error("File size exceeds 35MB limit");
    }
    return true;
};



/**
 * ==========================================
 * ENHANCED CITATION MANAGER API
 * ==========================================
 */

/**
 * Extract citations from a paper
 * @param {string} paperId - Paper ID
 * @param {boolean} useAiEnrichment - Whether to use AI for enrichment
 */ 

export async function extractCitations(paperId, useAiEnrichment = true){
    return apiRequest("/api/citations/extract", {
        method: "POST",
        body: JSON.stringify({
            paper_id: paperId,
            use_ai_enrichment: useAiEnrichment
        })
    });
}


/**
* Get extracted citations for a paper
* @param {string} paperId - Paper ID
*/

export async function getPaperCitations(paperId){
    return apiRequest(`/api/citations/paper/${paperId}`);
}


/**
 * Get citation statistics for a paper
 * @param {string} paperId - Paper ID
 */
export async function getCitationStats(paperId) {
  return apiRequest(`/api/citations/stats/${paperId}`);
}


/**
 * Generate citation in specific format
 * @param {string} paperId - Paper ID
 * @param {string} format - Citation format (apa, ieee, bibtex, etc.)
 */

export async function generateCitation(paperId, format = "apa"){
    return apiRequest("/api/citations/generate", {
        method: "POST",
        body: JSON.stringify({
            paper_id: paperId,
            format: format
        })
    });
}



/**
 * Generate batch citations
 * @param {array} paperIds - Array of paper IDs
 * @param {string} format - Citation format
 */
export async function generateBatchCitations(paperIds, format = 'apa') {
  return apiRequest('/api/citations/batch', {
    method: 'POST',
    body: JSON.stringify({
      paper_ids: paperIds,
      format: format
    })
  });
}


/**
 * Export citations as BibTeX
 * @param {array} paperIds - Array of paper IDs
 */

export async function exportBibTeX(paperIds) {
    const url = `${API_BASE_URL}/api/citations/export/bibtex`;

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            paper_ids: paperIds,
            format: "bibtex"
        })
    });

    if(!response.ok){
        throw new Error(`Error exporting BibTeX: ${response.statusText}`);
    }
    return response.text();
}


/**
 * Delete all citations for a paper
 * @param {string} paperId - Paper ID
 */
export async function deletePaperCitations(paperId) {
  return apiRequest(`/api/citations/paper/${paperId}/citations`, {
    method: 'DELETE'
  });
}

/**
 * Get available citation formats
 */
export async function getCitationFormats() {
  return apiRequest('/api/citations/formats');
}

/**
 * Verify a citation (mark as trusted)
 * @param {string} citationId - Citation ID
 */
export async function verifyCitation(citationId) {
  return apiRequest(`/api/citations/${citationId}/verify`, {
    method: 'PATCH'
  });
}

/**
 * Unverify a citation (remove trust mark)
 * @param {string} citationId - Citation ID
 */
export async function unverifyCitation(citationId) {
  return apiRequest(`/api/citations/${citationId}/unverify`, {
    method: 'PATCH'
  });
}

/**
 * Get verified citations for a paper
 * @param {string} paperId - Paper ID
 */
export async function getVerifiedCitations(paperId) {
  return apiRequest(`/api/citations/verified/${paperId}`);
}


// Export API configuration for use in other files
export const API_CONFIG = {
    BASE_URL: API_BASE_URL,
    ENDPOINTS: {
        UPLOAD: '/upload',
        SEARCH: '/search',
        PAPERS: '/papers',
        DIAGNOSTICS: '/qdrant/diagnostics',
        SYNTHESIS: '/synthesis',
        CITATIONS: '/api/citations',
    },
};


