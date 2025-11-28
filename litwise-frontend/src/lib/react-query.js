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
  processPaperAI,
  searchPapers, 
  getPapers, 
  getPaper, 
  deletePaper,
  getQdrantDiagnostics 
} from './api';
import { chatApi } from './chat-api';
import { useUploadStore, useSearchStore } from './stores';
import { toast } from 'sonner';

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

    return useMutation({
        mutationFn: uploadPaper,
        onMutate: async(file) => {
            // Start upload UI state
            startUpload(file);

            // Show loading toast
            toast.loading('Uploading PDF...', {
                id: 'upload-progress'
            });

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

            // Show success toast
            toast.success(
                `Paper "${data.title || 'Untitled'}" uploaded successfully!`,
                {
                    id: 'upload-progress',
                    description: 'Click "Generate AI Summary" to process with AI.',
                    duration: 5000
                }
            );

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

            // Show error toast
            toast.error(
                'Upload failed',
                {
                    id: 'upload-progress',
                    description: error.message || 'Failed to upload the PDF file.',
                    duration: 7000
                }
            );
        },
    });
}

/**
 * Custom Hook: Search Papers
 * 
 * Handle semantic search with filters, caching and state management
 */
export function useSearchPapers(){
    const {
        startSearch,
        finishSearch,
        failSearch,
    } = useSearchStore(); 

    return useMutation({
        mutationFn: ({ query, filters = null, debug = false, limit = 10 }) => 
            searchPapers(query, { filters, debug, limit }),
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
 * Custom Hook: Process Paper with AI
 * 
 * Handles AI processing with state management
 */
export function useProcessPaper() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: processPaperAI,
    
    onMutate: async (paperId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.papers.lists() });
      await queryClient.cancelQueries({ queryKey: queryKeys.papers.detail(paperId) });
      
      // Optimistically update paper status
      queryClient.setQueryData(queryKeys.papers.lists(), (old) => 
        old?.map(paper => 
          paper.id === paperId 
            ? { ...paper, processing_status: 'processing' }
            : paper
        ) || []
      );
      
      queryClient.setQueryData(queryKeys.papers.detail(paperId), (old) => 
        old ? { ...old, processing_status: 'processing' } : old
      );
    },
    
    onSuccess: (data, paperId) => {
      // Update with actual processed data
      queryClient.setQueryData(queryKeys.papers.lists(), (old) => 
        old?.map(paper => 
          paper.id === paperId 
            ? { ...paper, processing_status: 'completed', summary: data.summary }
            : paper
        ) || []
      );
    },
    
    onError: (error, paperId) => {
      // Update status to failed
      queryClient.setQueryData(queryKeys.papers.lists(), (old) => 
        old?.map(paper => 
          paper.id === paperId 
            ? { ...paper, processing_status: 'failed' }
            : paper
        ) || []
      );
    },
    
    onSettled: (data, error, paperId) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.detail(paperId) });
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
      
      // Get paper details for error message
      const papers = context?.previousPapers;
      const failedPaper = papers?.find(p => p.id === paperId);
      
      toast.error(
        'Failed to delete paper ❌',
        {
          description: `Could not delete "${failedPaper?.title || failedPaper?.filename || 'the paper'}". ${error.message || 'Please try again.'}`,
          duration: 6000,
          action: {
            label: "Retry",
            onClick: () => {
              // Could trigger retry logic here if needed
              toast.dismiss();
            }
          }
        }
      );
    },
    
    onSuccess: (data, paperId) => {
      // Get paper details for the success message
      const papers = queryClient.getQueryData(queryKeys.papers.lists());
      const deletedPaper = papers?.find(p => p.id === paperId);
      
      toast.success(
        'Paper deleted successfully! 🗑️',
        {
          description: `"${deletedPaper?.title || deletedPaper?.filename || 'Untitled Paper'}" has been permanently removed from your library.`,
          duration: 5000,
          action: {
            label: "Dismiss",
            onClick: () => toast.dismiss()
          }
        }
      );
    },
    
    onSettled: () => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
    },
  });
}


export const useChatSessions = (paperId) => {
  return useQuery({
    queryKey: ["chatsessions", paperId],
    queryFn: () => chatApi.getPaperSessions(paperId),
    enabled: !!paperId,
  });
};


export const useChatMessages = (sessionId) => {
  return useQuery({
    queryKey: ["chatmessages", sessionId],
    queryFn: () => chatApi.getSessionMessages(sessionId),
    enabled: !!sessionId,
  });
};


export const useCreateChatSession = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ paperId, title }) => chatApi.createSession(paperId, title),
    onSuccess: (data, { paperId }) => {
      queryClient.invalidateQueries(['chatsessions', paperId]);
    },
  });
}


export const useDeleteChatSession = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: chatApi.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries(['chatsessions']);
    },
  });
};

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