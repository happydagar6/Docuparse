/**
 * Enhanced Paper Reader Component with Pagination
 * 
 * Features:
 * - PDF-style pagination with page navigation
 * - Collapsible sidebar with close button
 * - Robust error handling and loading states
 * - Responsive design with keyboard shortcuts
 * - Page-based content display
 */

'use client';

import { useState, useRef, useLayoutEffect, useOptimistic, useCallback, useMemo, startTransition, useEffectEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  X,
  ArrowLeft, 
  BookOpen, 
  Brain, 
  Link2, 
  Download,
  Share2,
  Settings,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { FormattedContent, FormattedSummary } from '@/components/ui/formatted-content';
import { usePaperStore } from '@/lib/stores';

export function PaperReader({ paper, onBack }) {
  // Local state
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pageInputValue, setPageInputValue] = useState('');
  
  // Refs
  const contentRef = useRef(null);
  const sidebarRef = useRef(null);
  
  // Zustand store for paper reader state
  const {
    showSidebar,
    currentPage,
    totalPages,
    pageContent,
    pageError,
    fontSize,
    theme,
    highlightedSections,
    toggleSidebar,
    setCurrentPage,
    goToNextPage,
    goToPreviousPage,
    initializePagination,
    resetPagination,
    setFontSize,
    clearHighlights
  } = usePaperStore();
  
  // React 19.2: useOptimistic for page transitions - synced with store
  const [optimisticPage, setOptimisticPage] = useOptimistic(
    currentPage,
    (state, newPage) => newPage
  );

  /**
   * Initialize pagination when paper data loads - using React 19.2 patterns
   */
  const paperInitialization = useMemo(() => {
    if (!paper) return null;
    
    return async () => {
      setIsLoading(true);
      setError(null);

      try {
        const content = paper?.content || paper?.content_text || paper?.extracted_text;
        if (!content) {
          throw new Error('No content available for this paper');
        }

        // Try to parse page_info if available
        let pageInfo = null;
        if (paper.page_info) {
          try {
            pageInfo = typeof paper.page_info === 'string' 
              ? JSON.parse(paper.page_info) 
              : paper.page_info;
          } catch (parseError) {
            console.warn('Could not parse page_info:', parseError);
            pageInfo = null;
          }
        }

        // Initialize pagination with content and page info
        initializePagination(content, pageInfo);
        setPageInputValue('1');

      } catch (err) {
        console.error('Error initializing paper:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
  }, [paper, initializePagination]);

  // React 19.2: Initialize with useLayoutEffect for synchronous updates
  useLayoutEffect(() => {
    if (paperInitialization) {
      paperInitialization();
    }

    // Cleanup on unmount
    return () => {
      resetPagination();
    };
  }, [paperInitialization, resetPagination]);

  /**
   * Update page input when current page changes - React 19.2 optimized
   */
  useLayoutEffect(() => {
    startTransition(() => {
      setPageInputValue(currentPage.toString());
      setOptimisticPage(currentPage);
    });
  }, [currentPage, setOptimisticPage]);

  /**
   * Keyboard shortcuts with React 19.2 optimizations
   */
  const handleKeyboardNavigation = useCallback((e) => {
    if (e.target.tagName === 'INPUT') return;
    
    switch (e.key) {
      case 'ArrowLeft':
      case 'h':
        e.preventDefault();
        startTransition(() => {
          const prevPage = Math.max(1, currentPage - 1);
          setOptimisticPage(prevPage);
          goToPreviousPage();
        });
        break;
      case 'ArrowRight':
      case 'l':
        e.preventDefault();
        startTransition(() => {
          const nextPage = Math.min(totalPages, currentPage + 1);
          setOptimisticPage(nextPage);
          goToNextPage();
        });
        break;
      case 's':
        e.preventDefault();
        toggleSidebar();
        break;
      case 'Escape':
        if (showSidebar) {
          toggleSidebar();
        }
        break;
    }
  }, [goToPreviousPage, goToNextPage, toggleSidebar, showSidebar, currentPage, totalPages, setOptimisticPage]);

  useLayoutEffect(() => {
    window.addEventListener('keydown', handleKeyboardNavigation);
    return () => window.removeEventListener('keydown', handleKeyboardNavigation);
  }, [handleKeyboardNavigation]);

  /**
   * Handle page input change
   */
  const handlePageInputChange = (e) => {
    const value = e.target.value;
    setPageInputValue(value);
  };

  /**
   * Handle page input submit with optimistic updates
   */
  const handlePageInputSubmit = useCallback((e) => {
    e.preventDefault();
    const pageNum = parseInt(pageInputValue);
    if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
      startTransition(() => {
        setOptimisticPage(pageNum);
        setCurrentPage(pageNum);
      });
    } else {
      setPageInputValue(optimisticPage.toString());
    }
  }, [pageInputValue, totalPages, optimisticPage, setCurrentPage, setOptimisticPage]);

  /**
   * Font size controls
   */
  const increaseFontSize = useCallback(() => {
    const sizes = { small: 'medium', medium: 'large', large: 'large' };
    setFontSize(sizes[fontSize]);
  }, [fontSize, setFontSize]);

  const decreaseFontSize = useCallback(() => {
    const sizes = { small: 'small', medium: 'small', large: 'medium' };
    setFontSize(sizes[fontSize]);
  }, [fontSize, setFontSize]);

  /**
   * Get font size classes
   */
  const getFontSizeClass = () => {
    switch (fontSize) {
      case 'small': return 'text-sm';
      case 'large': return 'text-lg';
      default: return 'text-base';
    }
  };

  /**
   * Get current page content with optimistic updates
   */
  const getCurrentPageContent = useCallback(() => {
    if (pageError) {
      return {
        content: `Error loading page: ${pageError}`,
        pageNumber: optimisticPage
      };
    }

    if (!pageContent || pageContent.length === 0) {
      return {
        content: 'No content available',
        pageNumber: 1
      };
    }

    const page = pageContent.find(p => p.pageNumber === optimisticPage) || pageContent[0];
    return page;
  }, [pageError, pageContent, optimisticPage]);

  const currentPageData = useMemo(() => getCurrentPageContent(), [getCurrentPageContent]);

  /**
   * Sidebar content sections
   */
  const sidebarSections = [
    {
      id: 'summary',
      title: 'AI Summary',
      icon: Brain,
      content: paper?.summary
    },
    {
      id: 'key_points',
      title: 'Key Points',
      icon: BookOpen,
      content: paper?.summary?.key_points 
    },
    {
      id: 'related',
      title: 'Related Works',
      icon: Link2,
      content: paper?.summary?.related_works
    }
  ];

  // Loading state
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading paper...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <Card className="p-6 max-w-md">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Paper</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <div className="space-x-2">
              <Button onClick={onBack} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Go Back
              </Button>
              <Button 
                onClick={() => window.location.reload()} 
                variant="outline"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-white/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="px-6 py-4 flex items-center justify-between">
          {/* Left side - Navigation */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <h1 className="font-semibold text-lg truncate max-w-md">
                {paper?.title || paper?.filename || 'Research Paper'}
              </h1>
            </div>
          </div>
          
          {/* Center - Page Navigation */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                startTransition(() => {
                  setOptimisticPage(Math.max(1, optimisticPage - 1));
                  goToPreviousPage();
                });
              }}
              disabled={optimisticPage <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Page</span>
              <form onSubmit={handlePageInputSubmit}>
                <Input
                  type="text"
                  value={pageInputValue}
                  onChange={handlePageInputChange}
                  className="w-16 h-8 text-center text-sm"
                  onBlur={handlePageInputSubmit}
                />
              </form>
              <span className="text-sm text-muted-foreground">of {totalPages}</span>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                startTransition(() => {
                  setOptimisticPage(Math.min(totalPages, optimisticPage + 1));
                  goToNextPage();
                });
              }}
              disabled={optimisticPage >= totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Right side - Controls */}
          <div className="flex items-center gap-2">
            {/* Font size controls */}
            <Button
              variant="ghost"
              size="sm"
              onClick={decreaseFontSize}
              disabled={fontSize === 'small'}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={increaseFontSize}
              disabled={fontSize === 'large'}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            
            {/* Actions */}
            <Button variant="ghost" size="sm">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Share2 className="h-4 w-4" />
            </Button>
            
            {/* Sidebar toggle with label */}
            <Button
              variant={showSidebar ? "default" : "ghost"}
              size="sm"
              onClick={toggleSidebar}
              className="gap-2"
            >
              <BookOpen className="h-4 w-4" />
              {showSidebar ? 'Hide' : 'Show'} AI Insights
            </Button>
          </div>
        </div>
      </div>
      
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Paper Content */}
        <div 
          className={`flex-1 overflow-auto transition-all duration-300 ${
            showSidebar ? 'mr-96' : 'mr-0'
          }`}
        >
          <div 
            ref={contentRef}
            className="max-w-4xl mx-auto p-8"
          >
            {/* Page indicator */}
            <div className="mb-4 text-center">
              <span className="inline-flex items-center px-3 py-1 bg-primary/10 text-primary text-sm rounded-full">
                Page {optimisticPage} of {totalPages}
              </span>
            </div>

            {/* Page content */}
            <motion.div
              key={optimisticPage}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`prose max-w-none ${getFontSizeClass()}`}
            >
              <div className="min-h-[600px] p-6 bg-white rounded-lg shadow-sm border">
                <FormattedContent content={currentPageData.content} />
              </div>
            </motion.div>

            {/* Page navigation footer */}
            <div className="mt-8 flex justify-between items-center">
              <Button
                variant="outline"
                onClick={() => {
                  const prevPage = Math.max(1, currentPage - 1);
                  startTransition(() => {
                    setOptimisticPage(prevPage);
                    goToPreviousPage();
                  });
                }}
                disabled={currentPage <= 1}
                className="flex items-center gap-2"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous Page
              </Button>
              
              <span className="text-sm text-muted-foreground">
                Page {optimisticPage} of {totalPages}
              </span>
              
              <Button
                variant="outline"
                onClick={() => {
                  const nextPage = Math.min(totalPages, currentPage + 1);
                  startTransition(() => {
                    setOptimisticPage(nextPage);
                    goToNextPage();
                  });
                }}
                disabled={currentPage >= totalPages}
                className="flex items-center gap-2"
              >
                Next Page
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        
        {/* Enhanced Sidebar */}
        <AnimatePresence>
          {showSidebar && (
            <motion.div
              ref={sidebarRef}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 20 }}
              className="fixed right-0 top-[73px] bottom-0 w-96 bg-white border-l shadow-lg z-20 overflow-auto"
            >
              {/* Sidebar Header */}
              <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
                <h2 className="font-semibold text-lg">AI Insights</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleSidebar}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="p-6 space-y-6">
                {/* Sidebar sections */}
                {sidebarSections.map((section, index) => {
                  const IconComponent = section.icon;
                  
                  return (
                    <motion.div
                      key={section.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="flex items-center gap-2 text-base">
                            <IconComponent className="h-4 w-4" />
                            {section.title}
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm text-gray-700 leading-relaxed">
                          {section.id === 'summary' ? (
                            <FormattedSummary summary={section.content} />
                          ) : (
                            <FormattedContent 
                              content={section.content 
                                ? (Array.isArray(section.content) 
                                   ? section.content.map(item => `• ${item}`).join('\n')
                                   : section.content)
                                : `${section.title} will be generated based on the paper content.`
                              } 
                            />
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  );
                })}
                
                {/* Actions */}
                <div className="space-y-2 pt-4 border-t">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={clearHighlights}
                    className="w-full"
                  >
                    Clear Highlights
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setCurrentPage(1)}
                    className="w-full"
                  >
                    Go to First Page
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Keyboard shortcuts help */}
      <div className="absolute bottom-4 left-4 text-xs text-muted-foreground bg-white/80 backdrop-blur-sm px-2 py-1 rounded">
        <span className="hidden lg:inline">
          ← → Navigate • S Toggle sidebar • ESC Close sidebar
        </span>
      </div>
    </div>
  );
}