/**
 * Message Cache Manager
 * Efficient caching strategy for chat messages
 * 
 * Purpose:
 * - Cache messages in memory to avoid repeated API calls
 * - Keep most recent 1000 messages across all sessions
 * - Implement LRU (Least Recently Used) eviction
 * - Track cursor positions for pagination
 */

class MessageCacheManager {
  constructor(maxSize = 1000, sessionCacheSize = 5000) {
    this.maxSize = maxSize; // Max total messages
    this.sessionCacheSize = sessionCacheSize; // Max per session
    this.cache = new Map(); // sessionId -> { messages, cursor, timestamp }
    this.accessOrder = []; // Track LRU order
  }

  /**
   * Get cached messages for a session
   */
  get(sessionId) {
    if (!this.cache.has(sessionId)) {
      return null;
    }

    const entry = this.cache.get(sessionId);
    
    // Update LRU by moving to end
    this.accessOrder = this.accessOrder.filter(id => id !== sessionId);
    this.accessOrder.push(sessionId);
    
    // Update timestamp
    entry.timestamp = Date.now();
    
    return entry.messages;
  }

  /**
   * Get cursor for a session (for pagination)
   */
  getCursor(sessionId) {
    const entry = this.cache.get(sessionId);
    return entry?.cursor || null;
  }

  /**
   * Set cached messages for a session
   */
  set(sessionId, messages, cursor = null) {
    // Calculate new total size
    let totalSize = Array.from(this.cache.values()).reduce(
      (sum, entry) => sum + entry.messages.length,
      0
    );
    
    const newSize = (this.cache.get(sessionId)?.messages.length || 0) + messages.length;
    totalSize = totalSize - (this.cache.get(sessionId)?.messages.length || 0) + newSize;

    // Evict old sessions if needed
    while (totalSize > this.maxSize && this.accessOrder.length > 1) {
      const oldestSessionId = this.accessOrder.shift();
      const removedSize = this.cache.get(oldestSessionId)?.messages.length || 0;
      this.cache.delete(oldestSessionId);
      totalSize -= removedSize;
    }

    // Check per-session limit
    const sessionMessages = this.cache.get(sessionId)?.messages || [];
    if (sessionMessages.length > this.sessionCacheSize) {
      // Keep most recent messages, remove oldest
      sessionMessages.splice(
        0,
        sessionMessages.length - this.sessionCacheSize
      );
    }

    // Store or update
    if (!this.cache.has(sessionId)) {
      this.accessOrder.push(sessionId);
    } else {
      this.accessOrder = this.accessOrder.filter(id => id !== sessionId);
      this.accessOrder.push(sessionId);
    }

    this.cache.set(sessionId, {
      messages,
      cursor,
      timestamp: Date.now()
    });
  }

  /**
   * Append messages to cache (for infinite scroll)
   */
  append(sessionId, messages, cursor = null) {
    const entry = this.cache.get(sessionId);
    if (entry) {
      // Check for duplicates and remove old entries
      const existingIds = new Set(entry.messages.map(m => m.id));
      const newMessages = messages.filter(m => !existingIds.has(m.id));
      
      entry.messages.push(...newMessages);
      entry.cursor = cursor;
      
      // Keep size in check
      if (entry.messages.length > this.sessionCacheSize) {
        entry.messages.splice(
          0,
          entry.messages.length - this.sessionCacheSize
        );
      }
    } else {
      this.set(sessionId, messages, cursor);
    }
  }

  /**
   * Prepend messages to cache (for loading older messages)
   */
  prepend(sessionId, messages, cursor = null) {
    const entry = this.cache.get(sessionId);
    if (entry) {
      // Check for duplicates
      const existingIds = new Set(entry.messages.map(m => m.id));
      const newMessages = messages.filter(m => !existingIds.has(m.id));
      
      entry.messages = [...newMessages, ...entry.messages];
      entry.cursor = cursor;
      
      // Keep size in check
      if (entry.messages.length > this.sessionCacheSize) {
        entry.messages.splice(this.sessionCacheSize);
      }
    } else {
      this.set(sessionId, messages, cursor);
    }
  }

  /**
   * Clear cache for a session
   */
  clear(sessionId) {
    this.cache.delete(sessionId);
    this.accessOrder = this.accessOrder.filter(id => id !== sessionId);
  }

  /**
   * Clear all cache
   */
  clearAll() {
    this.cache.clear();
    this.accessOrder = [];
  }

  /**
   * Get cache stats for debugging
   */
  getStats() {
    const totalMessages = Array.from(this.cache.values()).reduce(
      (sum, entry) => sum + entry.messages.length,
      0
    );

    return {
      sessions: this.cache.size,
      totalMessages,
      maxSize: this.maxSize,
      accessOrder: this.accessOrder
    };
  }

  /**
   * Get cache size for a session
   */
  getSessionSize(sessionId) {
    return this.cache.get(sessionId)?.messages.length || 0;
  }
}

// Singleton instance
export const messageCache = new MessageCacheManager();

export default messageCache;
