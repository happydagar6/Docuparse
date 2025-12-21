/**
 * Literature Review API Functions
 * 
 * Client-side API functions for interacting with the Literature Review backend endpoints.
 */

import { apiRequest } from './api';

/**
 * Generate a new literature review
 */
export async function generateLiteratureReview(data) {
    return apiRequest('/api/literature-review/generate', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

/**
 * Get list of all literature reviews
 * Note: When called by React Query, no arguments are passed, so we use a fixed limit
 */
export async function getLiteratureReviews() {
    return apiRequest('/api/literature-review/list?limit=20');
}

/**
 * Get a specific literature review by ID
 */
export async function getLiteratureReview(reviewId) {
    return apiRequest(`/api/literature-review/${reviewId}`);
}

/**
 * Delete a literature review
 */
export async function deleteLiteratureReview(reviewId) {
    return apiRequest(`/api/literature-review/${reviewId}`, {
        method: 'DELETE',
    });
}
