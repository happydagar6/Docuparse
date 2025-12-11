/**
 * Literature Review API Functions
 * 
 * Client-side API functions for interacting with the Literature Review backend endpoints.
 */

import { getSupabaseClient } from './supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get JWT token from Supabase session
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
 * Generate a new literature review
 */
export async function generateLiteratureReview(data) {
    const token = await getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${API_URL}/api/literature-review/generate`, {
        method: 'POST',
        headers,
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
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${API_URL}/api/literature-review/list?limit=20`, { headers });
    if (!res.ok) throw new Error('Failed to fetch literature reviews');
    return res.json();
}

/**
 * Get a specific literature review by ID
 */
export async function getLiteratureReview(reviewId) {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${API_URL}/api/literature-review/${reviewId}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch literature review');
    return res.json();
}

/**
 * Delete a literature review
 */
export async function deleteLiteratureReview(reviewId) {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${API_URL}/api/literature-review/${reviewId}`, {
        headers,
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete literature review');
    return res.json();
}
