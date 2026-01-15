/**
 * Improved Search Form Component
 *
 * SIMPLIFIED FLOW:
 * 1. User sees Getting Started guide on first visit
 * 2. User enters natural language query (e.g., "deep learning papers")
 * 3. Click "Search" button
 * 4. Backend performs semantic search (5-phase pipeline)
 * 5. Results displayed with clear explanations
 * 6. User selects and navigates to papers
 *
 * KEY IMPROVEMENTS:
 * - Getting Started guide with examples
 * - Collapsed advanced filters (hidden by default)
 * - Relevance score explanations
 * - Better empty states
 * - Cleaner result cards with context
 */

"use client";

import {
  useState,
  useActionState,
  useOptimistic,
  useCallback,
  startTransition,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  FileText,
  Clock,
  X,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Info,
  Lightbulb,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSearchPapers } from "@/lib/react-query";
import { useSearchStore } from "@/lib/stores";
import { toast } from "sonner";

export function SearchForm({ onResultClick }) {
  // Local state for search input
  const [searchInput, setSearchInput] = useState("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showGettingStarted, setShowGettingStarted] = useState(true);
  const [useNLParsing] = useState(true);

  // Advanced filter state
  const [filters, setFilters] = useState({
    author: "",
    yearFrom: null,
    yearTo: null,
    keywords: [],
    hasImages: false,
    hasTables: false,
    hasEquations: false,
    venue: "",
  });

  // Zustand store for search state
  const {
    query,
    isSearching,
    searchResults,
    searchError,
    searchHistory,
    setQuery,
    clearSearch,
  } = useSearchStore();

  // React Query mutation for search
  const searchMutation = useSearchPapers();

  // React 19.2: useOptimistic for immediate UI feedback
  const [optimisticResults, addOptimisticResult] = useOptimistic(
    searchResults || [],
    (state, newResult) => [...state, newResult]
  );

  // React 19.2: useActionState for form handling
  const [searchState, searchAction, isPending] = useActionState(
    async (prevState, formData) => {
      const searchQuery = formData.get("query") || searchInput;
      if (!searchQuery.trim()) {
        return { error: "Please enter a search query" };
      }

      if (
        filters.yearFrom &&
        filters.yearTo &&
        filters.yearFrom > filters.yearTo
      ) {
        return {
          error: 'Year "From" must be less than "To"',
        };
      }

      try {
        // Update query in store
        startTransition(() => {
          setQuery(searchQuery);
          setShowGettingStarted(false);
        });

        // Build filters object
        const searchFilters = {};
        if (filters.author?.trim()) {
          searchFilters.author = filters.author.trim();
        }
        if (filters.yearFrom) {
          searchFilters.year_from = parseInt(filters.yearFrom);
        }
        if (filters.yearTo) {
          searchFilters.year_to = parseInt(filters.yearTo);
        }
        if (filters.keywords?.length > 0) {
          searchFilters.keywords = filters.keywords;
        }
        if (filters.hasImages) {
          searchFilters.has_images = true;
        }
        if (filters.hasTables) {
          searchFilters.has_tables = true;
        }
        if (filters.hasEquations) {
          searchFilters.has_equations = true;
        }
        if (filters.venue?.trim()) {
          searchFilters.venue = filters.venue.trim();
        }

        // Execute search
        await searchMutation.mutateAsync({
          query: searchQuery,
          filters:
            Object.keys(searchFilters).length > 0 ? searchFilters : undefined,
          use_nl_parsing: useNLParsing,
        });

        return {
          success: true,
          query: searchQuery,
          filtersApplied: Object.keys(searchFilters).length > 0,
        };
      } catch (error) {
        console.error("Search failed:", error);
        return {
          error: error.message || "Search failed. Please try again.",
        };
      }
    },
    { success: false }
  );

  const handleInputChange = useCallback((e) => {
    const value = e.target.value;
    setSearchInput(value);
  }, []);

  const handleHistoryClick = (historyQuery) => {
    setSearchInput(historyQuery);
  };

  const handleClear = () => {
    setSearchInput("");
    clearSearch();
    setShowGettingStarted(true);
  };

  const getScoreColor = (score) => {
    if (score >= 0.9) return "text-green-600 bg-green-50";
    if (score >= 0.8) return "text-blue-600 bg-blue-50";
    if (score >= 0.7) return "text-yellow-600 bg-yellow-50";
    return "text-orange-600 bg-orange-50";
  };

  const getScoreLabel = (score) => {
    if (score >= 0.9) return "Excellent Match";
    if (score >= 0.8) return "Very Good Match";
    if (score >= 0.7) return "Good Match";
    return "Relevant";
  };

  // Example searches for Getting Started
  const exampleSearches = [
    "deep learning architectures",
    "neural networks 2023-2025",
    "papers by John Doe",
    "climate modeling with tables",
    "computer vision with images",
  ];

  return (
    <div className="space-y-8">
      {/* Getting Started Guide */}
      <AnimatePresence>
        {showGettingStarted && searchResults.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-blue-200 bg-blue-50/30 backdrop-blur">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-blue-900">
                  <Lightbulb className="h-5 w-5" />
                  Getting Started with Smart Search
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Search Tips */}
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">
                      💡 Tips for Better Results
                    </h4>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex gap-2">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span>
                          <strong>Topics:</strong> &quot;neural networks&quot;, &quot;climate
                          change&quot;
                        </span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span>
                          <strong>Methods:</strong> &quot;how to train transformers&quot;
                        </span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span>
                          <strong>Authors:</strong> &quot;papers by Jane Smith&quot;
                        </span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span>
                          <strong>Time:</strong> &quot;2023-2025&quot; or &quot;recent papers&ldquo;
                        </span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-600 font-bold">✓</span>
                        <span>
                          <strong>Content:</strong> &quot;with images&quot;, &quot;with tables&quot;
                        </span>
                      </li>
                    </ul>
                  </div>

                  {/* Example Searches */}
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">
                      🎯 Try These Searches
                    </h4>
                    <div className="space-y-2">
                      {exampleSearches.map((example, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSearchInput(example);
                          }}
                          className="w-full text-left px-3 py-2 rounded-lg bg-white/60 hover:bg-white transition-colors border border-blue-200/50 text-sm text-gray-700 hover:text-blue-600 font-medium"
                        >
                          &quot;{example}&quot;
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* How Semantic Search Works */}
                <div className="mt-4 p-4 bg-white/50 rounded-lg border border-blue-100">
                  <h5 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-600" />
                    How It Works
                  </h5>
                  <p className="text-sm text-gray-700">
                    Our semantic search understands the <em>meaning</em> of your
                    query, not just keywords. Search for &quot;deep learning&quot; and
                    find papers about &quot;neural networks&quot;, &quot;transformers&quot;, and
                    related topics. Results are ranked by relevance (how well
                    they match your search).
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search Form */}
      <form action={searchAction} className="space-y-4">
        {/* Main Search Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            What papers are you looking for?
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Input
                name="query"
                value={searchInput}
                onChange={handleInputChange}
                placeholder="e.g., deep learning architectures, papers by 2023..."
                disabled={isPending}
                className="pl-4 pr-10 py-6 text-base border-2 border-gray-200 focus:border-blue-500"
              />
              {searchInput && !isPending && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <Button
              type="submit"
              disabled={isPending || !searchInput.trim()}
              className="px-6 h-14 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Advanced Filters - Collapsed by Default */}
        <motion.div
          initial={false}
          animate={{ height: showAdvancedFilters ? "auto" : 0 }}
          transition={{ duration: 0.3 }}
          className="overflow-hidden"
        >
          <Card className="border-gray-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Advanced Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Author Filter */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Author Name
                  </label>
                  <Input
                    placeholder="e.g., John Doe"
                    value={filters.author}
                    onChange={(e) =>
                      setFilters({ ...filters, author: e.target.value })
                    }
                    className="text-sm"
                  />
                </div>

                {/* Year Range */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      From Year
                    </label>
                    <Input
                      type="number"
                      placeholder="2020"
                      value={filters.yearFrom || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          yearFrom: e.target.value
                            ? parseInt(e.target.value)
                            : null,
                        })
                      }
                      className="text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      To Year
                    </label>
                    <Input
                      type="number"
                      placeholder="2025"
                      value={filters.yearTo || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          yearTo: e.target.value
                            ? parseInt(e.target.value)
                            : null,
                        })
                      }
                      className="text-sm"
                    />
                  </div>
                </div>

                {/* Venue Filter */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Conference/Journal
                  </label>
                  <Input
                    placeholder="e.g., ICML, Nature"
                    value={filters.venue}
                    onChange={(e) =>
                      setFilters({ ...filters, venue: e.target.value })
                    }
                    className="text-sm"
                  />
                </div>

                {/* Content Filters */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 block">
                    Content Type
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasImages}
                        onChange={(e) =>
                          setFilters({
                            ...filters,
                            hasImages: e.target.checked,
                          })
                        }
                        className="w-4 h-4 rounded"
                      />
                      <span className="text-sm text-gray-700">Images</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasTables}
                        onChange={(e) =>
                          setFilters({
                            ...filters,
                            hasTables: e.target.checked,
                          })
                        }
                        className="w-4 h-4 rounded"
                      />
                      <span className="text-sm text-gray-700">Tables</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.hasEquations}
                        onChange={(e) =>
                          setFilters({
                            ...filters,
                            hasEquations: e.target.checked,
                          })
                        }
                        className="w-4 h-4 rounded"
                      />
                      <span className="text-sm text-gray-700">Equations</span>
                    </label>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Toggle Advanced Filters */}
        <button
          type="button"
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
        >
          {showAdvancedFilters ? (
            <>
              <ChevronUp className="h-4 w-4" />
              Hide Advanced Filters
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              Show Advanced Filters
            </>
          )}
        </button>

        {/* Search History */}
        {searchHistory.length > 0 && searchResults.length === 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">
              Recent Searches
            </label>
            <div className="flex flex-wrap gap-2">
              {searchHistory.slice(0, 5).map((hist, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleHistoryClick(hist)}
                  className="px-3 py-1.5 rounded-full bg-gray-100 hover:bg-gray-200 text-sm text-gray-700 flex items-center gap-2 transition-colors"
                >
                  <Clock className="h-3 w-3" />
                  {hist}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error Display */}
        {searchState.error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3"
          >
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-900">
                {searchState.error}
              </p>
            </div>
          </motion.div>
        )}
      </form>

      {/* Search Results Section */}
      <AnimatePresence mode="wait">
        {isPending && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-3" />
            <p className="text-gray-600">Searching your papers...</p>
          </motion.div>
        )}

        {!isPending && searchResults.length > 0 && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Found {searchResults.length} relevant results
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClear}
                className="text-gray-600"
              >
                Clear Search
              </Button>
            </div>

            {/* Results List */}
            <div className="space-y-3">
              {optimisticResults.map((result, index) => {
                // Create unique key: combine paper_id with chunk_id for uniqueness
                // If no chunk_id, use index as fallback
                const uniqueKey = result.chunk_id 
                  ? `${result.paper_id || result.id}-${result.chunk_id}`
                  : (result.paper_id || result.id || `result-${index}`);
                
                return (
                <motion.div
                  key={uniqueKey}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card
                    className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-blue-500"
                    onClick={() => {
                      const paperId = result.paper_id || result.id;
                      const searchContext = {
                        chunk_id: result.chunk_id,
                        page: result.page,
                        content: result.content || result.text,
                        title: result.paper_title || result.title
                      };
                      console.log('[SearchForm] Result clicked:', { paperId, searchContext });
                      if (onResultClick && paperId) {
                        onResultClick(paperId, searchContext);
                      } else {
                        console.warn('[SearchForm] Cannot navigate - missing paper ID or callback', { onResultClick, paperId });
                      }
                    }}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1 min-w-0">
                          {/* Result Title */}
                          <h4 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                            {result.title || result.paper_title || "Untitled"}
                          </h4>

                          {/* Result Snippet */}
                          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                            {result.text || result.content || "No preview available"}
                          </p>

                          {/* Metadata Tags */}
                          <div className="flex flex-wrap gap-2 text-xs">
                            {result.publication_year && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded">
                                {result.publication_year}
                              </span>
                            )}
                            {result.authors &&
                              typeof result.authors !== 'undefined' &&
                              (Array.isArray(result.authors) ? result.authors.length > 0 : true) && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                  {Array.isArray(result.authors)
                                    ? result.authors
                                        .filter(a => a && typeof a === 'string')
                                        .slice(0, 2)
                                        .join(", ")
                                      + (result.authors.length > 2 ? " +more" : "")
                                    : typeof result.authors === 'string'
                                    ? result.authors
                                    : "Authors"}
                                </span>
                              )}
                          </div>
                        </div>

                        {/* Relevance Score */}
                        <div className="flex flex-col items-end gap-2">
                          {result.relevance_score && (
                            <div
                              className={`px-3 py-2 rounded-lg ${getScoreColor(
                                result.relevance_score
                              )} text-center`}
                              title={`Relevance score: ${(result.relevance_score * 100).toFixed(0)}% - ${getScoreLabel(result.relevance_score)}`}
                            >
                              <div className="font-bold text-sm">
                                {(result.relevance_score * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs font-medium">
                                {getScoreLabel(result.relevance_score)}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                );
              })}
            </div>

            {/* Relevance Score Explanation */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-gray-700">
                <strong>📊 Relevance Score:</strong> Shows how well each result
                matches your search. Higher scores = better matches. Click any
                result to read the full paper.
              </p>
            </div>
          </motion.div>
        )}

        {!isPending && query && searchResults.length === 0 && (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-12"
          >
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              No papers found
            </h4>
            <p className="text-gray-600 mb-4">
              Try adjusting your search query or filters
            </p>
            <Button
              variant="outline"
              onClick={handleClear}
              className="text-gray-600"
            >
              Clear and Try Again
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
