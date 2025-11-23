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
 * Manages paper reading interface state
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