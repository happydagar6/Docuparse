/**
 * React Query Configuration and Custom Hooks
 * 
 * This file sets up React Query for server state management:
 * - API caching and synchronization
 * - Optimistic updates
 * - Background refetching
 * - Error handling
 * - Custom hooks for each API endpoint
 */

import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  QueryClient,
  QueryClientProvider 
} from '@tanstack/react-query';
import { 
  uploadPaper, 
  searchPapers, 
  getPapers, 
  getPaper, 
  deletePaper,
  getQdrantDiagnostics 
} from './api';
import { useUploadStore, useSearchStore, useUIStore } from './stores';


// Query Client configuration

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Cache data for 5 minutes
            staleTime: 5 * 60 * 1000,

            // Keep in cache for 10 minutes
            gcTime: 10 * 60 * 1000,

            // Retry failed requests up to 2 times
            retry: 2,

            // Dont refetch on window focus in development
            refetchOnWindowFocus: process.env.NODE_ENV === 'production',
        },
        mutations: {
            // Retry failed mutations twice
            retry: 2,
        },
    },
});

// Query key factory
// Centrailized query key management for consistent caching

export const queryKeys = {
    papers: {
        all: () => ['papers'],
        lists: () => ['papers', 'lists'],
        list: (filters) => ['papers', 'list', filters],
        details: () => ['papers', 'details'],
        detail: (id) => ['papers', 'detail', id],
    },
    search: {
        all: () => ['search'],
        results: (query) => ['search', 'results', query],
    },
    diagnostics: {
        qdrant: () => ['diagnostics', 'qdrant'],
    },
};

// Custom Hooks
// Handle file upload with progress tracking and optimistic updates

export function useUploadPaper() {
    const queryClient = useQueryClient();
    const {
        startUpload,
        updateProgress,
        finishUpload,
        failUpload,
    } = useUploadStore();

    const { addNotification } = useUIStore(); // For user notifications.
    return useMutation({
        mutationFn: uploadPaper,
        onMutate: async(file) => {
            // Start upload UI state
            startUpload(file);

            // Simulate progress for better UX
            const progressInterval = setInterval(() => {
                updateProgress(Math.min(Math.random() * 30 + 10, 90));
            }, 300);
            return { progressInterval };
        },

        onSuccess: (data, variables, context) => {
            // Clear progress interval
            if(context?.progressInterval){
                clearInterval(context.progressInterval);
            }

            // Update progress to 100% and finish upload state
            updateProgress(100);
            finishUpload(data);

            // Show success notification
            addNotification({
                type: "success",
                title: "Upload Successful",
                message: `Paper "${data.title || 'Untitled'}" has been processed and is ready to view.`,
            });

            // Invalidate and refetch papers list
            queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
        },

        onError: (error, variables, context) => {
            // Clear progress interval
            if(context?.progressInterval){
                clearInterval(context.progressInterval);
            }

            // Update error state
            failUpload(error);

            // Show error notification
            addNotification({
                type: "error",
                title: "Upload Failed",
                message: error.message || "Failed to upload and process the PDF file.",
            });
        },
    });
}

// Custom hook to search papers with debounced input
// Handle semantic search and caching and state management

export function useSearchPapers(){
    const {
        startSearch,
        finishSearch,
        failSearch,
    } = useSearchStore(); 

    return useMutation({
        mutationFn: ({ query, debug = false }) => searchPapers(query, debug),
        onMutate: () => {
            startSearch();
        },

        onSuccess: (data) => {
            finishSearch(data);
        },

        onError: (error) => {
            failSearch(error);
        },
    });
}

/**
 * Custom Hook: Get Papers List
 * 
 * Fetches and caches all uploaded papers
 */
export function usePapers() {
  return useQuery({
    queryKey: queryKeys.papers.lists(),
    queryFn: getPapers,
    staleTime: 2 * 60 * 1000, // Consider stale after 2 minutes
  });
}

/**
 * Custom Hook: Get Paper Details
 * 
 * Fetches specific paper with caching
 */
export function usePaper(paperId) {
  return useQuery({
    queryKey: queryKeys.papers.detail(paperId),
    queryFn: () => getPaper(paperId),
    enabled: !!paperId, // Only run if paperId exists
    staleTime: 10 * 60 * 1000, // Paper details change less frequently
  });
}

/**
 * Custom Hook: Delete Paper
 * 
 * Handles paper deletion with optimistic updates
 */
export function useDeletePaper() {
  const queryClient = useQueryClient();
  const { addNotification } = useUIStore();

  return useMutation({
    mutationFn: deletePaper,
    
    onMutate: async (paperId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.papers.lists() });
      
      // Snapshot the previous value
      const previousPapers = queryClient.getQueryData(queryKeys.papers.lists());
      
      // Optimistically remove paper from list
      queryClient.setQueryData(queryKeys.papers.lists(), (old) => 
        old?.filter(paper => paper.id !== paperId) || []
      );
      
      return { previousPapers };
    },
    
    onError: (error, paperId, context) => {
      // Rollback on error
      if (context?.previousPapers) {
        queryClient.setQueryData(queryKeys.papers.lists(), context.previousPapers);
      }
      
      addNotification({
        type: 'error',
        title: 'Delete Failed',
        message: error.message || 'Failed to delete the paper.',
      });
    },
    
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'Paper Deleted',
        message: 'The paper has been successfully deleted.',
      });
    },
    
    onSettled: () => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
    },
  });
}

/**
 * Custom Hook: Qdrant Diagnostics
 * 
 * For debugging vector database state
 */
export function useQdrantDiagnostics() {
  return useQuery({
    queryKey: queryKeys.diagnostics.qdrant(),
    queryFn: getQdrantDiagnostics,
    enabled: process.env.NODE_ENV === 'development', // Only in development
    staleTime: 30 * 1000, // Refresh every 30 seconds
  });
}

/**
 * Query Client Provider Component
 * 
 * Wrap your app with this component to enable React Query
 */
export function QueryProvider({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}