/**
 * Performance Metrics Tracker
 * Monitors chat performance and provides analytics
 * 
 * Tracks:
 * - Message load times
 * - Pagination performance
 * - Memory usage
 * - User scroll patterns
 * - API response times
 */

class MessageMetricsTracker {
  constructor() {
    this.metrics = {
      loads: [], // Array of load events
      pagination: [],
      errors: [],
      memory: [],
      scrollPatterns: []
    };
    this.sessionMetrics = new Map(); // Per-session metrics
  }

  /**
   * Record message load time
   */
  recordLoadTime(sessionId, timeMs, messageCount, source = 'initial') {
    const metric = {
      timestamp: Date.now(),
      sessionId,
      timeMs,
      messageCount,
      source, // 'initial', 'pagination', 'refetch'
      perMessage: timeMs / messageCount
    };

    this.metrics.loads.push(metric);
    this.recordSessionMetric(sessionId, 'load', metric);

    // Log if slow
    if (timeMs > 1000) {
      console.warn(`Slow message load: ${timeMs}ms for ${messageCount} messages`);
    }

    return metric;
  }

  /**
   * Record pagination event
   */
  recordPagination(sessionId, direction, itemsLoaded, timeMs) {
    const metric = {
      timestamp: Date.now(),
      sessionId,
      direction, // 'older', 'newer'
      itemsLoaded,
      timeMs
    };

    this.metrics.pagination.push(metric);
    this.recordSessionMetric(sessionId, 'pagination', metric);
  }

  /**
   * Record API error
   */
  recordError(sessionId, error, action = 'load') {
    const metric = {
      timestamp: Date.now(),
      sessionId,
      error: error.message || String(error),
      action,
      stack: error.stack
    };

    this.metrics.errors.push(metric);
    this.recordSessionMetric(sessionId, 'error', metric);

    console.error(`Chat error (${action}):`, error);
  }

  /**
   * Record scroll pattern
   */
  recordScroll(sessionId, scrollDepth, direction) {
    const metric = {
      timestamp: Date.now(),
      sessionId,
      scrollDepth, // 0-100 percentage
      direction // 'up', 'down', 'jump'
    };

    this.metrics.scrollPatterns.push(metric);
  }

  /**
   * Record memory usage
   */
  recordMemory(sessionId, messageCount) {
    if (performance.memory) {
      const metric = {
        timestamp: Date.now(),
        sessionId,
        messageCount,
        heapUsed: performance.memory.usedJSHeapSize,
        heapLimit: performance.memory.jsHeapSizeLimit,
        percentage: (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
      };

      this.metrics.memory.push(metric);
      this.recordSessionMetric(sessionId, 'memory', metric);
    }
  }

  /**
   * Record per-session metric
   */
  recordSessionMetric(sessionId, type, metric) {
    if (!this.sessionMetrics.has(sessionId)) {
      this.sessionMetrics.set(sessionId, {});
    }

    const sessionData = this.sessionMetrics.get(sessionId);
    if (!sessionData[type]) {
      sessionData[type] = [];
    }

    sessionData[type].push(metric);

    // Keep only last 50 of each type
    if (sessionData[type].length > 50) {
      sessionData[type].shift();
    }
  }

  /**
   * Get average load time
   */
  getAverageLoadTime(source) {
    const filtered = source 
      ? this.metrics.loads.filter(m => m.source === source)
      : this.metrics.loads;

    if (filtered.length === 0) return 0;

    const sum = filtered.reduce((acc, m) => acc + m.timeMs, 0);
    return sum / filtered.length;
  }

  /**
   * Get average per-message load time
   */
  getAveragePerMessageTime(source) {
    const filtered = source
      ? this.metrics.loads.filter(m => m.source === source)
      : this.metrics.loads;

    if (filtered.length === 0) return 0;

    const sum = filtered.reduce((acc, m) => acc + m.perMessage, 0);
    return sum / filtered.length;
  }

  /**
   * Get session summary
   */
  getSessionSummary(sessionId) {
    const sessionData = this.sessionMetrics.get(sessionId);
    if (!sessionData) return null;

    const loads = sessionData.load || [];
    const paginations = sessionData.pagination || [];
    const errors = sessionData.error || [];

    return {
      sessionId,
      totalLoads: loads.length,
      totalPaginations: paginations.length,
      totalErrors: errors.length,
      avgLoadTime: loads.length > 0 
        ? loads.reduce((s, m) => s + m.timeMs, 0) / loads.length
        : 0,
      lastLoadTime: loads.length > 0 ? loads[loads.length - 1].timeMs : null,
      recentErrors: errors.slice(-5)
    };
  }

  /**
   * Get all metrics summary
   */
  getSummary() {
    return {
      loads: {
        total: this.metrics.loads.length,
        avgTime: this.getAverageLoadTime(),
        avgPerMessage: this.getAveragePerMessageTime()
      },
      pagination: {
        total: this.metrics.pagination.length,
        avgTime: this.metrics.pagination.length > 0
          ? this.metrics.pagination.reduce((s, m) => s + m.timeMs, 0) / this.metrics.pagination.length
          : 0
      },
      errors: {
        total: this.metrics.errors.length,
        recent: this.metrics.errors.slice(-5)
      },
      sessions: Array.from(this.sessionMetrics.keys()).map(sessionId =>
        this.getSessionSummary(sessionId)
      )
    };
  }

  /**
   * Reset metrics
   */
  reset() {
    this.metrics = {
      loads: [],
      pagination: [],
      errors: [],
      memory: [],
      scrollPatterns: []
    };
    this.sessionMetrics.clear();
  }

  /**
   * Export metrics for analytics
   */
  export() {
    return {
      summary: this.getSummary(),
      raw: this.metrics,
      generatedAt: new Date().toISOString()
    };
  }
}

// Singleton instance
export const metricsTracker = new MessageMetricsTracker();

// Enable in development
if (process.env.NODE_ENV === 'development') {
  window.__metricsTracker = metricsTracker;
  console.log('Metrics tracker available at window.__metricsTracker');
}

export default metricsTracker;
