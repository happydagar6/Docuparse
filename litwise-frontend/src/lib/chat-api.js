import { getSupabaseClient } from './supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

export const chatApi = {
  // Create a new chat session
  createSession: async (paperId, title) => {
    const token = await getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(`${API_BASE_URL}/api/chat/sessions?paper_id=${paperId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  // Get chat sessions for a paper
  getPaperSessions: async (paperId) => {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${paperId}`, { headers });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },


  // Get paginated chat messages for a session
  getPaginatedMessages: async (sessionId, limit = 20, cursor = null, direction = 'before') => {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const params = new URLSearchParams({
      limit,
      direction,
    });
    if (cursor) params.append('cursor', cursor);

    const response = await fetch(
      `${API_BASE_URL}/api/chat/sessions/${sessionId}/messages/paginated?${params}`,
      { headers }
    );
    
    if(!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  },

  // Get message count for a session
  getMessageCount: async (sessionId) => {
    const token = await getAuthToken(); // Get auth token
    const headers = {}; // Prepare headers
    if (token) headers['Authorization'] = `Bearer ${token}`; // Add auth header if token exists

    const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}/messages/count`, { headers });
    if(!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  // Get messages for a session
  getSessionMessages: async (sessionId) => {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`, { headers });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: {response.status}`);
    }

    return response.json();
  },

  // Stream chat response with abort support
  streamChat: async (sessionId, message, onChunk, abortSignal = null) => {
    // Removed console.log for chat stream start
    
    const token = await getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
      }),
      signal: abortSignal, // Add abort signal support
    });

    // Removed console.log for stream response status
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onChunk(data);
            } catch (e) {
              console.error('Error parsing chunk:', e, 'Line:', line);
            }
          }
        }
      }
    } catch (error) {
      // If aborted, don't throw error - it's intentional
      if (error.name === 'AbortError') {
        // Removed console.log for stream aborted by user
        onChunk({ type: 'aborted', message: 'Generation stopped by user' });
        return;
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  },

  // Delete a chat session
  deleteSession: async (sessionId) => {
    const token = await getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },
};