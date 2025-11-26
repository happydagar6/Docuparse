/**
 * Zustand State Management for Litwise UI
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
      highlightedSections: new Set(),
      activeSection: null,
      
      // Pagination state
      currentPage: 1,
      totalPages: 0,
      pagesPerView: 1, // pages to show at once
      pageContent: [], // array of page content
      pageError: null,
      
      // Reader settings
      fontSize: 'medium', // 'small', 'medium', 'large'
      theme: 'light', // 'light', 'dark'
      
      // Actions
      setCurrentPaper: (paper) => 
        set({ currentPaper: paper }),

      toggleSidebar: () => 
        set((state) => ({ showSidebar: !state.showSidebar })),

      highlightSection: (sectionId) => 
        set((state) => ({
          highlightedSections: new Set([...state.highlightedSections, sectionId])
        })),

      unhighlightSection: (sectionId) => 
        set((state) => {
          const newHighlights = new Set(state.highlightedSections);
          newHighlights.delete(sectionId);
          return { highlightedSections: newHighlights };
        }),

      setActiveSection: (sectionId) => 
        set({ activeSection: sectionId }),

      setFontSize: (size) => 
        set({ fontSize: size }),

      setTheme: (theme) => 
        set({ theme }),

      clearHighlights: () => 
        set({ highlightedSections: new Set() }),

      // Pagination actions
      setCurrentPage: (pageNumber) => {
        const state = get();
        const validPage = Math.max(1, Math.min(pageNumber, state.totalPages));
        set({ currentPage: validPage });
      },

      goToNextPage: () => {
        const state = get();
        if (state.currentPage < state.totalPages) {
          set({ currentPage: state.currentPage + 1 });
        }
      },

      goToPreviousPage: () => {
        const state = get();
        if (state.currentPage > 1) {
          set({ currentPage: state.currentPage - 1 });
        }
      },

      initializePagination: (content, pageInfo = null) => {
        try {
          let pageContent = [];
          let totalPages = 1;

          if (pageInfo && Array.isArray(pageInfo) && pageInfo.length > 0) {
            // Use page info from PDF extraction
            pageContent = pageInfo.map((page, index) => ({
              pageNumber: index + 1,
              content: page.text || '',
              startPos: page.start_pos || 0,
              endPos: page.end_pos || 0
            }));
            totalPages = pageContent.length;
          } else if (content) {
            // Fallback: split content into estimated pages (every 2000 characters)
            const charsPerPage = 2000;
            const totalChars = content.length;
            totalPages = Math.ceil(totalChars / charsPerPage);
            
            for (let i = 0; i < totalPages; i++) {
              const start = i * charsPerPage;
              const end = Math.min((i + 1) * charsPerPage, totalChars);
              pageContent.push({
                pageNumber: i + 1,
                content: content.slice(start, end),
                startPos: start,
                endPos: end
              });
            }
          }

          set({ 
            pageContent, 
            totalPages, 
            currentPage: 1, 
            pageError: null 
          });
        } catch (error) {
          console.error('Error initializing pagination:', error);
          set({ 
            pageError: error.message,
            pageContent: [{ 
              pageNumber: 1, 
              content: content || '', 
              startPos: 0, 
              endPos: content?.length || 0 
            }],
            totalPages: 1,
            currentPage: 1
          });
        }
      },

      resetPagination: () => 
        set({
          currentPage: 1,
          totalPages: 0,
          pageContent: [],
          pageError: null
        }),
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
            type: 'info', // 'success', 'error', 'warning', 'info'
            ...notification
          }]
        })),

      removeNotification: (id) => 
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),

      setGlobalLoading: (isLoading, message = '') => 
        set({ isLoading, loadingMessage: message }),

      setIsMobile: (isMobile) => 
        set({ isMobile }),

      clearNotifications: () => 
        set({ notifications: [] }),
    }),
    {
      name: 'ui-store',
    }
  )
);