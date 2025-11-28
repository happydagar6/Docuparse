/**
 * Search Form Component
 * 
 * Provides semantic search interface for uploaded papers.
 * 
 * COMPONENT LOGIC FLOW:
 * 1. User enters search query
 * 2. Query sent to FastAPI /search endpoint
 * 3. Backend generates embeddings → queries Qdrant → returns relevant papers
 * 4. Results displayed with similarity scores
 * 5. Optional debug mode for detailed search insights
 * 
 * FEATURES:
 * - Real-time search as user types (debounced)
 * - Search history and suggestions
 * - Advanced search filters
 * - Result ranking and scoring
 * - Empty states and loading indicators
 */

'use client';

import { useState, useActionState, useOptimistic, useCallback, startTransition, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  FileText, 
  Clock, 
  Settings, 
  X, 
  Loader2,
  AlertCircle 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormattedSummary } from '@/components/ui/formatted-content';
import { useSearchPapers } from '@/lib/react-query';
import { useSearchStore } from '@/lib/stores';

export function SearchForm({ onResultClick }) {
  // Local state for search input
  const [searchInput, setSearchInput] = useState('');
  
  // Advanced filter state
  const [filters, setFilters] = useState({
    author: '',
    yearFrom: null,
    yearTo: null,
    keywords: []
  });
  
  // Zustand store for search state
  const {
    query,
    isSearching,
    searchResults,
    searchError,
    searchHistory,
    showAdvancedSearch,
    setQuery,
    clearSearch,
    toggleAdvancedSearch
  } = useSearchStore();

  // React 19.2: useOptimistic for immediate UI feedback
  // Ensure initial state is always an array (never null/undefined)
  const [optimisticResults, addOptimisticResult] = useOptimistic(
    searchResults || [],
    (state, newResult) => [...state, newResult]
  );
  
  // React Query mutation for search
  const searchMutation = useSearchPapers();

  // React 19.2: useActionState for form handling
  const [searchState, searchAction, isPending] = useActionState(
    async (prevState, formData) => {
      const searchQuery = formData.get('query') || searchInput;
      if (!searchQuery.trim()) {
        return { error: 'Please enter a search query' };
      }

      // Validate year range if provided
      if (filters.yearFrom && filters.yearTo && filters.yearFrom > filters.yearTo) {
        return { error: 'Year range "From" must be less than or equal to "To"' };
      }

      try {
        // Update query in store with transition
        startTransition(() => {
          setQuery(searchQuery);
        });
        
        // Build filters object for API
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
        
        // Execute search mutation with filters
        const result = await searchMutation.mutateAsync({ 
          query: searchQuery,
          filters: Object.keys(searchFilters).length > 0 ? searchFilters : undefined,
          debug: process.env.NODE_ENV === 'development' 
        });

        return { 
          success: true, 
          query: searchQuery,
          resultCount: result?.length || 0,
          filtersApplied: Object.keys(searchFilters).length > 0
        };
      } catch (error) {
        console.error('Search failed:', error);
        return { 
          error: error.message || 'Search failed. Please try again.' 
        };
      }
    },
    { success: false }
  );

  // Debounced search using useCallback
  const performSearchRef = useRef();
  
  useEffect(() => {
    performSearchRef.current = (query) => {
      if (query.trim()) {
        // Trigger form submission programmatically
        const form = document.querySelector('form[data-search-form]');
        if (form) {
          form.requestSubmit();
        }
      }
    };
  });

  const debouncedSearch = useMemo(() => {
    let timeoutId;
    return (query) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        if (performSearchRef.current) {
          performSearchRef.current(query);
        }
      }, 500);
    };
  }, []);

  /**
   * Handle search input changes with modern debouncing
   */
  const handleInputChange = useCallback((e) => {
    const value = e.target.value;
    setSearchInput(value);
    debouncedSearch(value);
  }, [debouncedSearch]);

  /**
   * Handle search history item click
   */
  const handleHistoryClick = (historyQuery) => {
    setSearchInput(historyQuery);
    // Trigger form submission after input is set
    setTimeout(() => {
      const form = document.querySelector('form[data-search-form]');
      if (form) {
        form.requestSubmit();
      }
    }, 0);
  };

  /**
   * Clear search and reset form
   */
  const handleClear = () => {
    setSearchInput('');
    clearSearch();
  };

  /**
   * Calculate relevance score color
   */
  const getScoreColor = (score) => {
    if (score > 0.8) return 'text-green-600';
    if (score > 0.6) return 'text-blue-600';
    if (score > 0.4) return 'text-yellow-600';
    return 'text-gray-600';
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Semantic Search
          </CardTitle>
        </CardHeader>
        
        <CardContent>
          <form action={searchAction} data-search-form className="space-y-4">
            {/* Main Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                name="query"
                placeholder="Search for research topics, methodologies, findings..."
                value={searchInput}
                onChange={handleInputChange}
                className="pl-10 pr-20"
              />
              
              {/* Action buttons */}
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-1">
                {searchInput && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleClear}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
                
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={toggleAdvancedSearch}
                  className="h-6 w-6 p-0"
                >
                  <Settings className="h-3 w-3" />
                </Button>
              </div>
            </div>
            
            {/* Advanced Search */}
            <AnimatePresence>
              {showAdvancedSearch && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="p-4 bg-gray-50 rounded-lg space-y-3"
                >
                  <h4 className="text-sm font-medium">Advanced Options</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Author
                      </label>
                      <Input 
                        placeholder="Author name" 
                        size="sm"
                        value={filters.author}
                        onChange={(e) => setFilters(prev => ({ ...prev, author: e.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Year Range
                      </label>
                      <div className="flex gap-2">
                        <Input 
                          placeholder="From" 
                          size="sm"
                          type="number"
                          min="1900"
                          max="2100"
                          value={filters.yearFrom || ''}
                          onChange={(e) => setFilters(prev => ({ ...prev, yearFrom: e.target.value ? parseInt(e.target.value) : null }))}
                        />
                        <Input 
                          placeholder="To" 
                          size="sm"
                          type="number"
                          min="1900"
                          max="2100"
                          value={filters.yearTo || ''}
                          onChange={(e) => setFilters(prev => ({ ...prev, yearTo: e.target.value ? parseInt(e.target.value) : null }))}
                        />
                      </div>
                    </div>
                  </div>
                  {/* Clear filters button */}
                  {(filters.author || filters.yearFrom || filters.yearTo) && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setFilters({ author: '', yearFrom: null, yearTo: null, keywords: [] })}
                      className="text-xs"
                    >
                      <X className="h-3 w-3 mr-1" />
                      Clear Filters
                    </Button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Submit Button */}
            <Button 
              type="submit" 
              disabled={!searchInput.trim() || isPending}
              className="w-full"
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search Papers
                </>
              )}
            </Button>

            {/* Search state feedback */}
            {searchState?.error && (
              <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                {searchState.error}
              </div>
            )}
            {searchState?.success && (
              <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
                Found {searchState.resultCount} result(s) for "{searchState.query}"
                {searchState.filtersApplied && (
                  <span className="ml-1 text-xs">(with filters applied)</span>
                )}
              </div>
            )}
          </form>
        </CardContent>
      </Card>
      
      {/* Search History */}
      {searchHistory.length > 0 && !optimisticResults.length && !isSearching && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Recent Searches
            </h4>
            <div className="flex flex-wrap gap-2">
              {searchHistory.map((historyQuery, index) => (
                <button
                  key={index}
                  onClick={() => handleHistoryClick(historyQuery)}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
                >
                  {historyQuery}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Search Results */}
      <AnimatePresence>
        {optimisticResults.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Search Results ({optimisticResults.length})</span>
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    Clear Results
                  </Button>
                </CardTitle>
              </CardHeader>
              
              <CardContent>
                <div className="space-y-4">
                  {optimisticResults.map((result, index) => (
                    <motion.div
                      key={result.id || index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className={`p-4 border rounded-lg transition-colors cursor-pointer ${
                        result.isOptimistic 
                          ? 'border-blue-200 bg-blue-50' 
                          : 'border-gray-200 hover:border-primary'
                      }`}
                      onClick={() => !result.isOptimistic && onResultClick?.(result)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <FileText className="h-4 w-4 text-blue-500" />
                            <h4 className="font-medium text-gray-900">
                              {result.title || result.metadata?.title || 'Untitled Paper'}
                            </h4>
                          </div>
                          
                          {result.summary && (
                            <div className="text-sm text-gray-600 mb-2 line-clamp-3">
                              <FormattedSummary summary={result.summary} />
                            </div>
                          )}
                          
                          {result.metadata && (
                            <div className="text-xs text-gray-500">
                              {result.metadata.created_at && (
                                <span>
                                  Uploaded {new Date(result.metadata.created_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        
                        {/* Relevance Score */}
                        <div className="ml-4 text-right">
                          <div className={`text-sm font-medium ${getScoreColor(result.score || result.relevance_score || 0)}`}>
                            {((result.score || result.relevance_score || 0) * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-400">
                            relevance
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Search Error */}
      {searchError && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-red-500" />
                <div>
                  <p className="text-sm font-medium text-red-800">
                    Search Failed
                  </p>
                  <p className="text-sm text-red-600">{searchError}</p>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={handleClear}
                  className="ml-auto"
                >
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
      
      {/* No Results */}
      {optimisticResults.length === 0 && !isPending && query && !searchError && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <CardContent className="pt-6 text-center">
              <Search className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h4 className="font-medium text-gray-900 mb-2">
                No papers found
              </h4>
              <p className="text-sm text-gray-600">
                Try adjusting your search terms or upload more papers to expand your collection.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}