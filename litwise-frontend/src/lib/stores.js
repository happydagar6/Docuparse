/**
 * Zustand State Management for DocuParse UI
 * 
 * This file manages lightweight UI state that doesn't require server synchronization:
 * - Upload progress and status
 * - UI toggles (highlights, sidebars, modals)
 * - Current paper view state
 * - Search interface state
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

/**
 * Upload State Store
 * 
 * Manages file upload progress and status
 */
export const useUploadStore = create(
  devtools(
    (set, get) => ({
      // Current upload state
      isUploading: false,
      uploadProgress: 0,
      uploadedFile: null,
      uploadError: null,
      uploadSuccess: false,

      // Actions
      startUpload: (file) => 
        set({ 
          isUploading: true, 
          uploadProgress: 0, 
          uploadedFile: file,
          uploadError: null,
          uploadSuccess: false 
        }),

      updateProgress: (progress) => 
        set({ uploadProgress: Math.min(progress, 100) }),

      finishUpload: (result) => 
        set({ 
          isUploading: false, 
          uploadProgress: 100, 
          uploadSuccess: true,
          uploadError: null 
        }),

      failUpload: (error) => 
        set({ 
          isUploading: false, 
          uploadError: error.message || 'Upload failed',
          uploadSuccess: false 
        }),

      resetUpload: () => 
        set({ 
          isUploading: false,
          uploadProgress: 0,
          uploadedFile: null,
          uploadError: null,
          uploadSuccess: false 
        }),
    }),
    {
      name: 'upload-store',
    }
  )
);

/**
 * Paper Reader State Store
 * 
 * Manages paper reading interface state with pagination
 */
export const usePaperStore = create(
  devtools(
    (set, get) => ({
      // Current paper being viewed
      currentPaper: null,
      
      // UI state
      showSidebar: true,
      showHighlights: false,
      fontSize: 'medium', // 'small', 'medium', 'large'
      
      // Pagination state (managed by PaperPDFViewer/AdvancedPDFViewer, not here)
      // Keeping only for backward compatibility if needed
      currentPage: 1,
      totalPages: 0,
      
      // Actions
      setCurrentPaper: (paper) => 
        set({ 
          currentPaper: paper,
          currentPage: 1
        }),

      toggleSidebar: () => 
        set((state) => ({ 
          showSidebar: !state.showSidebar 
        })),

      toggleHighlights: () => 
        set((state) => ({ 
          showHighlights: !state.showHighlights 
        })),

      setFontSize: (size) => 
        set({ fontSize: size }),

      // Pagination actions - NO LONGER NEEDED
      // All pagination is now handled by PaperPDFViewer and AdvancedPDFViewer components
      // These methods are kept as stubs for backward compatibility only
    }),
    {
      name: 'paper-store',
    }
  )
);

/**
 * Search State Store
 * 
 * Manages search interface state
 */
export const useSearchStore = create(
  devtools(
    (set, get) => ({
      // Search state
      query: '',
      isSearching: false,
      searchResults: [],
      searchError: null,
      
      // Search history
      searchHistory: [],
      
      // UI state
      showAdvancedSearch: false,
      selectedFilters: {
        dateRange: null,
        categories: [],
        authors: [],
      },

      // Actions
      setQuery: (query) => 
        set({ query }),

      startSearch: () => 
        set({ 
          isSearching: true, 
          searchError: null 
        }),

      finishSearch: (results) => 
        set((state) => ({ 
          isSearching: false,
          searchResults: results,
          searchHistory: [
            ...state.searchHistory.filter(q => q !== state.query),
            state.query
          ].slice(-10) // Keep last 10 searches
        })),

      failSearch: (error) => 
        set({ 
          isSearching: false,
          searchError: error.message || 'Search failed',
          searchResults: []
        }),

      clearSearch: () => 
        set({ 
          query: '',
          searchResults: [],
          searchError: null 
        }),

      toggleAdvancedSearch: () => 
        set((state) => ({ 
          showAdvancedSearch: !state.showAdvancedSearch 
        })),

      setFilters: (filters) => 
        set({ selectedFilters: filters }),
    }),
    {
      name: 'search-store',
    }
  )
);

/**
 * Global UI State Store
 * 
 * Manages app-wide UI state
 */
export const useUIStore = create(
  devtools(
    (set, get) => ({
      // Navigation
      currentPage: 'home', // 'home', 'upload', 'search', 'papers', 'reader'
      
      // Notifications
      notifications: [],
      
      // Global loading states
      isLoading: false,
      loadingMessage: '',
      
      // Mobile responsive
      isMobile: false,
      
      // Actions
      setCurrentPage: (page) => 
        set({ currentPage: page }),

      addNotification: (notification) => 
        set((state) => ({
          notifications: [...state.notifications, {
            id: Date.now(),
            timestamp: new Date(),
            ...notification
          }]
        })),

      removeNotification: (id) => 
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),

      clearNotifications: () => 
        set({ notifications: [] }),

      setLoading: (isLoading, message = '') => 
        set({ isLoading, loadingMessage: message }),

      setIsMobile: (isMobile) => 
        set({ isMobile }),
    }),
    {
      name: 'ui-store',
    }
  )
);

/**
 * Multi-Modal Content Store
 * Manages images and tables for papers
 */
export const useMultiModalStore = create(
  devtools(
    (set, get) => ({
      // Content cache: { paperId: { images: [], tables: [], ... } }
      contentCache: new Map(),
      
      // Loading states: { paperId: boolean }
      loadingStates: new Map(),
      
      // Error states: { paperId: string }
      errorStates: new Map(),
      
      // UI state
      selectedImage: null, // Currently viewed image
      selectedTable: null, // Currently viewed table
      zoomLevel: 1.0,
      
      // Actions
      
      /**
       * Set multimodal content for a paper (caches it)
       */
      setContent: (paperId, content) => {
        const cache = new Map(get().contentCache);
        cache.set(paperId, {
          images: content.images || [],
          tables: content.tables || [],
          total_images: content.total_images || 0,
          total_tables: content.total_tables || 0,
          loadedAt: Date.now(),
        });
        set({ contentCache: cache });
      },
      
      /**
       * Get cached content for a paper
       */
      getContent: (paperId) => {
        return get().contentCache.get(paperId) || null;
      },
      
      /**
       * Check if content is cached
       */
      isCached: (paperId) => {
        return get().contentCache.has(paperId);
      },
      
      /**
       * Set loading state
       */
      setLoading: (paperId, isLoading) => {
        const states = new Map(get().loadingStates);
        states.set(paperId, isLoading);
        set({ loadingStates: states });
      },
      
      /**
       * Get loading state
       */
      isLoading: (paperId) => {
        return get().loadingStates.get(paperId) || false;
      },
      
      /**
       * Set error state
       */
      setError: (paperId, error) => {
        const states = new Map(get().errorStates);
        if (error) {
          states.set(paperId, error);
        } else {
          states.delete(paperId);
        }
        set({ errorStates: states });
      },
      
      /**
       * Get error state
       */
      getError: (paperId) => {
        return get().errorStates.get(paperId) || null;
      },
      
      /**
       * Select an image for viewing
       */
      selectImage: (image) => set({ selectedImage: image, selectedTable: null }),
      
      /**
       * Select a table for viewing
       */
      selectTable: (table) => set({ selectedTable: table, selectedImage: null }),
      
      /**
       * Close selected content
       */
      closeSelected: () => set({ selectedImage: null, selectedTable: null }),
      
      /**
       * Set zoom level
       */
      setZoomLevel: (level) => set({ zoomLevel: Math.max(0.5, Math.min(3.0, level)) }),
      
      /**
       * Reset zoom
       */
      resetZoom: () => set({ zoomLevel: 1.0 }),
      
      /**
       * Clear cache for a paper
       */
      clearCache: (paperId) => {
        const cache = new Map(get().contentCache);
        cache.delete(paperId);
        const loading = new Map(get().loadingStates);
        loading.delete(paperId);
        const errors = new Map(get().errorStates);
        errors.delete(paperId);
        set({ 
          contentCache: cache, 
          loadingStates: loading, 
          errorStates: errors 
        });
      },
      
      /**
       * Clear all caches
       */
      clearAllCaches: () => set({ 
        contentCache: new Map(), 
        loadingStates: new Map(), 
        errorStates: new Map(),
        selectedImage: null,
        selectedTable: null,
        zoomLevel: 1.0,
      }),
    }),
    {
      name: 'multimodal-store',
    }
  )
);




/**
 * Citation Store
 * 
 * Manages citation extraction and display state
 */
export const useCitationStore = create(
  devtools(
    (set, get) => ({
      // Citation data
      citations: {}, // { paperId: [citations] }
      citationStats: {}, // { paperId: stats }
      
      // UI state
      isExtracting: false,
      extractionProgress: 0,
      extractionError: null,
      selectedCitations: [],
      filterType: 'all', // 'all', 'background', 'method', 'comparison', 'data'
      sortBy: 'importance', // 'importance', 'year', 'mentions'
      
      // Actions
      setCitations: (paperId, citations) =>
        set((state) => ({
          citations: {
            ...state.citations,
            [paperId]: citations
          }
        })),
      
      setCitationStats: (paperId, stats) =>
        set((state) => ({
          citationStats: {
            ...state.citationStats,
            [paperId]: stats
          }
        })),
      
      startExtraction: () =>
        set({
          isExtracting: true,
          extractionProgress: 0,
          extractionError: null
        }),
      
      finishExtraction: () =>
        set({
          isExtracting: false,
          extractionProgress: 100,
          extractionError: null
        }),
      
      failExtraction: (error) =>
        set({
          isExtracting: false,
          extractionError: error.message || 'Extraction failed'
        }),
      
      toggleCitationSelection: (citationId) =>
        set((state) => {
          const selected = state.selectedCitations.includes(citationId)
            ? state.selectedCitations.filter(id => id !== citationId)
            : [...state.selectedCitations, citationId];
          return { selectedCitations: selected };
        }),
      
      selectAllCitations: (citationIds) =>
        set({ selectedCitations: citationIds }),
      
      clearSelection: () =>
        set({ selectedCitations: [] }),
      
      setFilterType: (type) =>
        set({ filterType: type }),
      
      setSortBy: (sortBy) =>
        set({ sortBy }),
      
      resetCitationStore: () =>
        set({
          citations: {},
          citationStats: {},
          isExtracting: false,
          extractionProgress: 0,
          extractionError: null,
          selectedCitations: [],
          filterType: 'all',
          sortBy: 'importance'
        })
    }),
    {
      name: 'citation-store'
    }
  )
);