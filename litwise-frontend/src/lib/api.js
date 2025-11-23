/**
 * API Integration Layer for Litwise Backend
 * 
 * This file centralizes all API calls to the FastAPI backend.
 * It handles:
 * - HTTP requests with proper error handling
 * - Response formatting
 * - Environment configuration
 * - Request/response interceptors
 */

// API base configuration

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic API request handler
 * @param {string} endpoint - API endpoint path
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise} - API response data
 */

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
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
 * Upload PDF file to backend
 * 
 * Flow:
 * 1. Create FormData with PDF file
 * 2. POST to /upload endpoint
 * 3. Backend extracts text → runs LangGraph pipeline → stores in Supabase/Qdrant
 * 4. Returns paper metadata and summary
 * 
 * @param {File} file - PDF file to upload
 * @param {function} onProgress - Progress callback (optional)
 * @returns {Promise<object>} - Upload result with paper data
 */

export async function uploadPaper(file, onProgress){
    const formData = new FormData(); // Create FormData
    formData.append('file', file); // Append PDF file

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: "POST",
            body: formData,

            // Note: Dont set Content-Type header for FormData, browser sets it automatically
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
 * Search papers using semantic search
 * 
 * Flow:
 * 1. Send query text to /search endpoint
 * 2. Backend generates embeddings → queries Qdrant → returns relevant papers
 * 3. Results include similarity scores and metadata
 * 
 * @param {string} query - Search query text
 * @param {boolean} debug - Enable debug mode for detailed response
 * @returns {Promise<Array>} - Array of matching papers with scores
 */

export async function searchPapers(query, debug = false) {
  return apiRequest('/search', {
    method: 'POST',
    body: JSON.stringify({ 
      query,
      debug 
    }),
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
 * Utility function to validate file before upload
 * 
 * @param {File} file - File to validate
 * @throws {Error} - If validation fails
 */


export function validatePDFFile(file){
    const maxSize = 10 * 1024 * 1024; // 10MB limit
    const allowedTypes = ['application/pdf'];

    if(!file){
        throw new Error('No file selected');
    }

    if(!allowedTypes.includes(file.type)){
        throw new Error("Please select a valid PDF file");
    }

    if(file.size > maxSize){
        throw new Error("File size exceeds 10MB limit");
    }
    return true;
};


// Export API configuration for use in other files
export const API_CONFIG = {
    BASE_URL: API_BASE_URL,
    ENDPOINTS: {
        UPLOAD: '/upload',
        SEARCH: '/search',
        PAPERS: '/papers',
        DIAGNOSTICS: '/qdrant/diagnostics',
    },
};
