/**
 * Literature Review API Functions
 * 
 * Client-side API functions for interacting with the Literature Review backend endpoints.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate a new literature review
 */
export async function generateLiteratureReview(data) {
    const res = await fetch(`${API_URL}/api/literature-review/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || `Error generating literature review: ${res.statusText}`);
    }
    return res.json();
}

/**
 * Get list of all literature reviews
 * Note: When called by React Query, no arguments are passed, so we use a fixed limit
 */
export async function getLiteratureReviews() {
    const res = await fetch(`${API_URL}/api/literature-review/list?limit=20`);
    if (!res.ok) throw new Error('Failed to fetch literature reviews');
    return res.json();
}

/**
 * Get a specific literature review by ID
 */
export async function getLiteratureReview(reviewId) {
    const res = await fetch(`${API_URL}/api/literature-review/${reviewId}`);
    if (!res.ok) throw new Error('Failed to fetch literature review');
    return res.json();
}

/**
 * Delete a literature review
 */
export async function deleteLiteratureReview(reviewId) {
    const res = await fetch(`${API_URL}/api/literature-review/${reviewId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete literature review');
    return res.json();
}
