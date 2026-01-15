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
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  uploadPaper,
  processPaperAI,
  searchPapers,
  getPapers,
  getPaper,
  deletePaper,
  getQdrantDiagnostics,
  generateQuiz,
  getQuiz,
  submitQuizAttempt,
  getQuizAnalytics,
  getUserQuizzes,
  deleteQuiz, // Phase 1: Synthesis API
  getResearchMaterialsStats,
} from "./api";
import { chatApi } from "./chat-api";
import { useUploadStore, useSearchStore } from "./stores";
import { toast } from "sonner";

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
      refetchOnWindowFocus: process.env.NODE_ENV === "production",
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
    all: () => ["papers"],
    lists: () => ["papers", "lists"],
    list: (filters) => ["papers", "list", filters],
    details: () => ["papers", "details"],
    detail: (id) => ["papers", "detail", id],
  },
  search: {
    all: () => ["search"],
    results: (query) => ["search", "results", query],
  },
  diagnostics: {
    qdrant: () => ["diagnostics", "qdrant"],
  },
  quiz: {
    all: () => ["quiz"],
    lists: () => ["quiz", "lists"],
    list: () => ["quiz", "list"],
    myQuizzes: () => ["quiz", "my-quizzes"],
    details: () => ["quiz", "details"],
    detail: (id) => ["quiz", "detail", id],
    analytics: (id) => ["quiz", "analytics", id],
  },
};

// Custom Hooks
// Handle file upload with progress tracking and optimistic updates

export function useUploadPaper() {
  const queryClient = useQueryClient();
  const { startUpload, updateProgress, finishUpload, failUpload } =
    useUploadStore();

  return useMutation({
    mutationFn: uploadPaper,
    onMutate: async (file) => {
      // Start upload UI state
      startUpload(file);

      // Show loading toast
      toast.loading("Uploading PDF...", {
        id: "upload-progress",
      });

      // Simulate smooth progress for better UX
      // Uses exponential easing to slow down as it approaches 95%
      let currentProgress = 0;
      const progressInterval = setInterval(() => {
        // Increment with decreasing rate as we approach 95%
        // This creates a smooth, realistic progression
        if (currentProgress < 30) {
          // Fast start (0-30%)
          currentProgress += Math.random() * 8 + 5;
        } else if (currentProgress < 60) {
          // Medium pace (30-60%)
          currentProgress += Math.random() * 5 + 3;
        } else if (currentProgress < 85) {
          // Slower pace (60-85%)
          currentProgress += Math.random() * 3 + 1.5;
        } else {
          // Very slow as we approach 95%
          currentProgress += Math.random() * 1.5 + 0.5;
        }
        
        // Cap at 95% until server completes
        currentProgress = Math.min(currentProgress, 95);
        updateProgress(Math.floor(currentProgress));
      }, 400);
      return { progressInterval };
    },

    onSuccess: (data, variables, context) => {
      // Clear progress interval
      if (context?.progressInterval) {
        clearInterval(context.progressInterval);
      }

      // Update progress to 100% and finish upload state
      updateProgress(100);
      finishUpload(data);

      // Show success toast
      toast.success(
        `Paper "${data.title || "Untitled"}" uploaded successfully!`,
        {
          id: "upload-progress",
          description: 'Click "Generate AI Summary" to process with AI.',
          duration: 5000,
        }
      );

      // Invalidate and refetch papers list
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
    },

    onError: (error, variables, context) => {
      // Clear progress interval
      if (context?.progressInterval) {
        clearInterval(context.progressInterval);
      }

      // Update error state
      failUpload(error);

      // Show error toast
      toast.error("Upload failed", {
        id: "upload-progress",
        description: error.message || "Failed to upload the PDF file.",
        duration: 7000,
      });
    },
  });
}

/**
 * Custom Hook: Search Papers
 *
 * Handle semantic search with filters, caching and state management
 */
export function useSearchPapers() {
  const { startSearch, finishSearch, failSearch } = useSearchStore();

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
      await queryClient.cancelQueries({
        queryKey: queryKeys.papers.detail(paperId),
      });

      // Optimistically update paper status
      queryClient.setQueryData(
        queryKeys.papers.lists(),
        (old) =>
          old?.map((paper) =>
            paper.id === paperId
              ? { ...paper, processing_status: "processing" }
              : paper
          ) || []
      );

      queryClient.setQueryData(queryKeys.papers.detail(paperId), (old) =>
        old ? { ...old, processing_status: "processing" } : old
      );
    },

    onSuccess: (data, paperId) => {
      // Update with actual processed data
      queryClient.setQueryData(
        queryKeys.papers.lists(),
        (old) =>
          old?.map((paper) =>
            paper.id === paperId
              ? {
                  ...paper,
                  processing_status: "completed",
                  summary: data.summary,
                }
              : paper
          ) || []
      );
    },

    onError: (error, paperId) => {
      // Update status to failed
      queryClient.setQueryData(
        queryKeys.papers.lists(),
        (old) =>
          old?.map((paper) =>
            paper.id === paperId
              ? { ...paper, processing_status: "failed" }
              : paper
          ) || []
      );
    },

    onSettled: (data, error, paperId) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.papers.lists() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.papers.detail(paperId),
      });
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
    mutationFn: ({ paperId }) => deletePaper(paperId),

    onMutate: async ({ paperId, paperTitle }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.papers.lists() });

      // Snapshot the previous value
      const previousPapers = queryClient.getQueryData(queryKeys.papers.lists());

      // Optimistically remove paper from list
      queryClient.setQueryData(
        queryKeys.papers.lists(),
        (old) => old?.filter((paper) => paper.id !== paperId) || []
      );

      return { previousPapers, paperTitle };
    },

    onError: (error, { paperId, paperTitle }, context) => {
      // Rollback on error
      if (context?.previousPapers) {
        queryClient.setQueryData(
          queryKeys.papers.lists(),
          context.previousPapers
        );
      }

      toast.error("Failed to delete paper ❌", {
        description: `Could not delete "${
          paperTitle || "the paper"
        }". ${error.message || "Please try again."}`,
        duration: 6000,
        action: {
          label: "Retry",
          onClick: () => {
            // Could trigger retry logic here if needed
            toast.dismiss();
          },
        },
      });
    },

    onSuccess: (data, { paperId, paperTitle }) => {
      toast.success("Paper deleted successfully! 🗑️", {
        description: `"${
          paperTitle || "Paper"
        }" has been permanently removed from your library.`,
        duration: 5000,
        action: {
          label: "Dismiss",
          onClick: () => toast.dismiss(),
        },
      });
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
      queryClient.invalidateQueries(["chatsessions", paperId]);
    },
  });
};

export const useDeleteChatSession = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: chatApi.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries(["chatsessions"]);
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
    enabled: process.env.NODE_ENV === "development", // Only in development
    staleTime: 30 * 1000, // Refresh every 30 seconds
  });
}



// ============================================
// QUIZ HOOKS
// ============================================

/**
 * Generate a new quiz
 */

export function useGenerateQuiz() {
  const queryClient = useQueryClient(); // Get query client instance

  return useMutation({
    mutationFn: ({ paperId, config }) => generateQuiz(paperId, config),
    onSuccess: (data) => {
      // Cache the generate quiz detail
      queryClient.setQueryData(queryKeys.quiz.detail(data.id), data);

      // Invalidate user's quiz list
      queryClient.invalidateQueries({
        queryKey: queryKeys.quiz.myQuizzes(),
      });
      toast.success("Quiz generated successfully! 🎉");
    },
    onError: (error) => {
      toast.error("Failed to generate quiz ❌", {
        description: error.message || "Please try again.",
        duration: 2500,
      })
    }
  });
}



/**
 * Get quiz by ID
 */

export function useGetQuiz(quizId, enabled = true){
  return useQuery({
    queryKey: queryKeys.quiz.detail(quizId),
    queryFn: () => getQuiz(quizId),
    enabled: !!quizId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes // What is gc time? Garbage collection time
  });
}


/**
 * Submit quiz attempt
 */
export function useSubmitQuizAttempt() {
  const queryClient = useQueryClient(); // Get query client instance for cache management

  return useMutation({
    mutationFn: ({ quizId, attempt }) =>
      submitQuizAttempt(quizId, attempt),
    onSuccess: (data, variables) => {
      // Cache the analytics data for the quiz
      queryClient.setQueryData(
        queryKeys.quiz.analytics(variables.quizId),
        data
      );
      toast.success("Quiz submitted successfully! 🎉");
    },
    onError: (error) => {
      toast.error("Failed to submit quiz ❌", {
        description: error.message || "Please try again.",
        duration: 2000,
      })
    }
  })
}


/**
 * Get quiz analytics
 */

export function useGetQuizAnalytics(quizId, enabled = true) {
  return useQuery({
    queryKey: queryKeys.quiz.analytics(quizId),
    queryFn: () => getQuizAnalytics(quizId),
    enabled: !!quizId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get user's quizzes
 */

export function useGetUserQuizzes() {
  return useQuery({
    queryKey: queryKeys.quiz.myQuizzes(),
    queryFn: async () => {
      const response = await getUserQuizzes();
      // Backend returns { quizzes: [...] }, extract the array
      return response.quizzes || [];
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Delete a quiz
 */

export function useDeleteQuiz() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (quizId) => deleteQuiz(quizId),
    onSuccess: (data, quizId) => {
      // Remove quiz from user's quiz list cache
      queryClient.removeQueries({
        queryKey: queryKeys.quiz.detail(quizId),
      });

      // Invalidate user's quiz list
      queryClient.invalidateQueries({
        queryKey: queryKeys.quiz.myQuizzes(),
      });
      toast.success("Quiz deleted successfully! 🗑️");
    },
    onError: (error) => {
      toast.error("Failed to delete quiz ❌", {
        description: error.message || "Please try again.",
        duration: 2000,
      })
    }
  })
}

/**
 * Get research materials statistics (literature reviews + study plans + quizzes)
 */
export function useResearchMaterialsStats() {
  return useQuery({
    queryKey: ["research-materials", "stats"],
    queryFn: async () => {
      const response = await getResearchMaterialsStats();
      return response || {
        literature_reviews: 0,
        study_plans: 0,
        quizzes: 0,
        total: 0
      };
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - stats don't change often
  });
}



/**
 * Query Client Provider Component
 *
 * Wrap your app with this component to enable React Query
 */
export function QueryProvider({ children }) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
