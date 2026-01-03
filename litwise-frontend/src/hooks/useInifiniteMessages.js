// Custom hook for managing infinite scrolling messages
import { chatApi } from '@/lib/chat-api';
import { useCallback, useState, useRef, useEffect} from 'react';


export function useInfiniteMessages(sessionId, pageSize = 20) {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [error, setError] = useState(null);

    const cursorRef = useRef(null); // To track pagination cursor
    const oldestCursorRef = useRef(null); // To track oldest message cursor
    const initialLoadDoneRef = useRef(false); // To prevent multiple initial loads

    // Load initial messages (most recent) - will be cached on backend (Redis L2 cache)
    const loadInitial = useCallback(async () => {
        if (!sessionId || initialLoadDoneRef.current) return;

        setIsLoading(true);
        
        try {
            // Fetch from API - Backend Redis cache handles caching (L2 cache)
            const { messages: newMessages, next_cursor, has_more, total_count } = 
                await chatApi.getPaginatedMessages(sessionId, pageSize, null, 'before');

            // Sort messages chronologically for display
            const sortedMessages = newMessages.sort((a, b) => 
                new Date(a.created_at) - new Date(b.created_at)
            );
            
            setMessages(sortedMessages);
            cursorRef.current = next_cursor;
            oldestCursorRef.current = newMessages.length > 0 ? newMessages[newMessages.length - 1].created_at : null;
            setHasMore(has_more);
            setTotalCount(total_count);
            initialLoadDoneRef.current = true;
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [sessionId, pageSize]);

    // Load older messages for infinite scroll - Backend Redis cache handles caching
    const loadOlder = useCallback(async () => {
        if (!sessionId || !hasMore || isLoading || !cursorRef.current) return;

        setIsLoading(true);
        
        try {
            const { messages: newMessages, next_cursor, has_more } =
                await chatApi.getPaginatedMessages(sessionId, pageSize, cursorRef.current, 'before');

            if (newMessages.length === 0) {
                setHasMore(false); // No more messages to load
                return;
            }

            // Prepend older messages and sort
            setMessages(prev => [
                ...newMessages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)),
                ...prev
            ]);

            cursorRef.current = next_cursor;
            setHasMore(has_more);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [sessionId, pageSize, hasMore, isLoading]);

    // Add new messages optimistically, then sync
    const addMessage = useCallback((message) => {
        setMessages(prev => [...prev, message]);
    }, []);

    // Update message after streaming completed
    const updateMessage = useCallback((messageId, updates) => {
        setMessages(prev => prev.map(msg => 
            msg.id === messageId ? { ...msg, ...updates } : msg
        ));
    }, []);

    // Reset pagination
    const reset = useCallback(() => {
        setMessages([]);
        setIsLoading(false);
        setHasMore(true);
        setError(null);
        cursorRef.current = null;
        oldestCursorRef.current = null;
        initialLoadDoneRef.current = false;
    }, []);

    // Load initial messages on mount or sessionId change
    useEffect(() => {
        reset(); // Reset state
        loadInitial(); // Load messages
    }, [sessionId, loadInitial, reset]);

    return {
        messages,
        isLoading,
        hasMore,
        totalCount,
        error,
        loadOlder,
        addMessage,
        updateMessage,
        reset,
    };
}

export default useInfiniteMessages;