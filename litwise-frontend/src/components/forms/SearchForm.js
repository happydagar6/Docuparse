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

import { useState, useEffect, useCallback } from 'react';
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
  
  // React Query mutation for search
  const searchMutation = useSearchPapers();

  /**
   * Handle search execution
   */
  const handleSearch = useCallback(async (searchQuery = searchInput) => {
    if (!searchQuery.trim()) return;
    
    // Update query in store
    setQuery(searchQuery);
    
    try {
      // Execute search mutation
      await searchMutation.mutateAsync({ 
        query: searchQuery,
        debug: process.env.NODE_ENV === 'development' 
      });
    } catch (error) {
      console.error('Search failed:', error);
    }
  }, [searchInput, setQuery, searchMutation]);

  /**
   * Handle search input changes with debounce
   */
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchInput.trim() && searchInput !== query) {
        handleSearch(searchInput);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(debounceTimer);
  }, [searchInput, query, handleSearch]);

  /**
   * Handle search form submission
   */
  const handleSubmit = (e) => {
    e.preventDefault();
    handleSearch();
  };

  /**
   * Handle search history item click
   */
  const handleHistoryClick = (historyQuery) => {
    setSearchInput(historyQuery);
    handleSearch(historyQuery);
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
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Main Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search for research topics, methodologies, findings..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
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
                        />
                        <Input 
                          placeholder="To" 
                          size="sm"
                          type="number"
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Submit Button */}
            <Button 
              type="submit" 
              disabled={!searchInput.trim() || isSearching}
              className="w-full"
            >
              {isSearching ? (
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
          </form>
        </CardContent>
      </Card>
      
      {/* Search History */}
      {searchHistory.length > 0 && !searchResults.length && !isSearching && (
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
        {searchResults.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Search Results ({searchResults.length})</span>
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    Clear Results
                  </Button>
                </CardTitle>
              </CardHeader>
              
              <CardContent>
                <div className="space-y-4">
                  {searchResults.map((result, index) => (
                    <motion.div
                      key={result.id || index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="p-4 border border-gray-200 rounded-lg hover:border-primary transition-colors cursor-pointer"
                      onClick={() => onResultClick?.(result)}
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
                          <div className={`text-sm font-medium ${getScoreColor(result.score)}`}>
                            {(result.score * 100).toFixed(1)}%
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
      {searchResults.length === 0 && !isSearching && query && !searchError && (
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