/**
 * Synthesis History Page
 * 
 * View all saved synthesis results with filtering, searching, and management.
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Calendar, 
  FileText, 
  Trash2, 
  Eye, 
  Loader2,
  AlertCircle,
  Search,
  Filter,
  Tag,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { PageLayout } from '@/components/layout/Layout';
import { getSynthesisHistory, deleteSynthesis } from '@/lib/api';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function SynthesisHistoryPage() {
  const router = useRouter();
  const [syntheses, setSyntheses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [synthesisToDelete, setSynthesisToDelete] = useState(null);
  
  // Pagination state
  const ITEMS_PER_PAGE = 6;
  const [visibleCount, setVisibleCount] = useState(ITEMS_PER_PAGE);
  
  // Fetch synthesis history
  const loadHistory = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getSynthesisHistory(50, 0, tagFilter || null);
      setSyntheses(data.items || []);
    } catch (err) {
      setError(err.message);
      toast.error('Failed to load history', {
        description: err.message
      });
    } finally {
      setIsLoading(false);
    }
  }, [tagFilter]);
  
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);
  
  const handleDelete = async (synthesisId) => {
    try {
      await deleteSynthesis(synthesisId);
      setSyntheses(prev => prev.filter(s => s.id !== synthesisId));
      toast.success('Synthesis deleted successfully');
      setDeleteDialogOpen(false);
      setSynthesisToDelete(null);
    } catch (err) {
      toast.error('Failed to delete synthesis', {
        description: err.message
      });
    }
  };
  
  const openDeleteDialog = (synthesis) => {
    setSynthesisToDelete(synthesis);
    setDeleteDialogOpen(true);
  };
  
  const handleView = (synthesisId) => {
    router.push(`/synthesis/${synthesisId}`);
  };
  
  // Filter syntheses based on search query
  const filteredSyntheses = syntheses.filter(synthesis => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return synthesis.query.toLowerCase().includes(query);
  });
  
  // Paginate filtered results
  const visibleSyntheses = filteredSyntheses.slice(0, visibleCount);
  const hasMore = visibleCount < filteredSyntheses.length;
  const showingMore = visibleCount > ITEMS_PER_PAGE;
  
  // Handlers for Show More/Less
  const handleShowMore = () => {
    setVisibleCount(prev => prev + ITEMS_PER_PAGE);
  };
  
  const handleShowLess = () => {
    setVisibleCount(ITEMS_PER_PAGE);
  };
  
  // Reset visible count when search changes
  React.useEffect(() => {
    setVisibleCount(ITEMS_PER_PAGE);
  }, [searchQuery]);
  
  return (
    <PageLayout>
      {/* Enhanced Header Section */}
      <div className="mb-8">
        <div className="relative bg-linear-to-br from-purple-50 via-pink-50 to-rose-50 rounded-2xl p-8 md:p-10 border border-purple-100/50 overflow-hidden">
          {/* Glassmorphic background elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-linear-to-br from-purple-200 to-pink-200 rounded-full blur-3xl opacity-20 -z-10"></div>
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-linear-to-tr from-pink-200 to-rose-200 rounded-full blur-3xl opacity-15 -z-10"></div>
          
          <div className="relative z-10 flex items-start gap-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg">
              <Brain className="h-7 w-7 text-purple-600" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">AI Synthesis</h1>
              <p className="text-gray-700 leading-relaxed">Create comprehensive syntheses that combine insights from multiple documents with advanced AI analysis.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full max-w-6xl mx-auto space-y-6">
        {/* Search and Filter Bar */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search synthesis by query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Button
                variant="outline"
                onClick={loadHistory}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Refresh'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
          </div>
        )}
        
        {/* Error State */}
        {error && !isLoading && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-red-500" />
                <div>
                  <p className="text-sm font-medium text-red-800">Failed to load history</p>
                  <p className="text-sm text-red-600">{error}</p>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={loadHistory}
                  className="ml-auto"
                >
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Synthesis List */}
        {!isLoading && !error && (
          <>
            {filteredSyntheses.length === 0 ? (
              <Card>
                <CardContent className="pt-6 text-center py-12">
                  <Brain className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  <h4 className="font-medium text-gray-900 mb-2">
                    No saved syntheses yet
                  </h4>
                  <p className="text-sm text-gray-600 mb-4">
                    Generate and save syntheses from the Search page to see them here.
                  </p>
                  <Button onClick={() => router.push('/search')}>
                    Go to Search
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Showing count indicator */}
                <div className="flex items-center justify-between text-sm text-gray-500 px-1">
                  <span>
                    Showing {Math.min(visibleCount, filteredSyntheses.length)} of {filteredSyntheses.length} syntheses
                  </span>
                </div>
                
                <AnimatePresence>
                  {visibleSyntheses.map((synthesis, index) => (
                    <motion.div
                      key={synthesis.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <Card className="hover:shadow-lg transition-shadow">
                        <CardHeader className="p-4 sm:p-6">
                          <div className="flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <Brain className="h-5 w-5 text-purple-600 shrink-0" />
                                <CardTitle className="text-base sm:text-lg line-clamp-2">
                                  {synthesis.query}
                                </CardTitle>
                              </div>
                              
                              <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600">
                                <div className="flex items-center gap-1">
                                  <FileText className="h-3 w-3 sm:h-4 sm:w-4" />
                                  {synthesis.paper_count} papers
                                </div>
                                <div className="flex items-center gap-1">
                                  <Brain className="h-3 w-3 sm:h-4 sm:w-4" />
                                  {synthesis.theme_count} themes
                                </div>
                                <div className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3 sm:h-4 sm:w-4" />
                                  {new Date(synthesis.created_at).toLocaleDateString()}
                                </div>
                              </div>
                              
                              {synthesis.tags && synthesis.tags.length > 0 && (
                                <div className="flex flex-wrap items-center gap-2 mt-3">
                                  {synthesis.tags.map((tag, i) => (
                                    <Badge key={i} variant="secondary" className="text-xs">
                                      <Tag className="h-3 w-3 mr-1" />
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2 shrink-0">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleView(synthesis.id)}
                              >
                                <Eye className="h-4 w-4 mr-2" />
                                View
                              </Button>
                              <AlertDialog open={deleteDialogOpen && synthesisToDelete?.id === synthesis.id} onOpenChange={(open) => {
                                setDeleteDialogOpen(open);
                                if (!open) setSynthesisToDelete(null);
                              }}>
                                <AlertDialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => openDeleteDialog(synthesis)}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Delete Synthesis?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Are you sure you want to delete this synthesis? This action cannot be undone.
                                    </AlertDialogDescription>
                                    <div className="mt-2 text-sm font-medium text-gray-900">
                                      Query: &quot;{synthesis.query}&quot;
                                    </div>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel onClick={() => {
                                      setDeleteDialogOpen(false);
                                      setSynthesisToDelete(null);
                                    }}>
                                      Cancel
                                    </AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => handleDelete(synthesis.id)}
                                      className="bg-red-600 hover:bg-red-700"
                                    >
                                      Delete
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            </div>
                          </div>
                        </CardHeader>
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
                
                {/* Show More / Show Less Buttons */}
                {(hasMore || showingMore) && (
                  <div className="flex items-center justify-center gap-3 pt-4">
                    {hasMore && (
                      <Button
                        variant="outline"
                        onClick={handleShowMore}
                        className="flex items-center gap-2"
                      >
                        <ChevronDown className="h-4 w-4" />
                        Show More ({filteredSyntheses.length - visibleCount} remaining)
                      </Button>
                    )}
                    
                    {showingMore && (
                      <Button
                        variant="ghost"
                        onClick={handleShowLess}
                        className="flex items-center gap-2 text-gray-600"
                      >
                        <ChevronUp className="h-4 w-4" />
                        Show Less
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </PageLayout>
  );
}
