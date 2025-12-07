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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FormattedContent, FormattedSummary } from '@/components/ui/formatted-content';
import { usePaperStore } from '@/lib/stores';
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar';
import MultiModalContent from './MultiModalContent';
import { Image as ImageIcon } from 'lucide-react';
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
   * useEffectEvent ensures we always use latest functions without re-adding event listener
   */
  const handleKeyboardNavigation = useEffectEvent((e) => {
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
  });

  useLayoutEffect(() => {
    window.addEventListener('keydown', handleKeyboardNavigation);
    return () => window.removeEventListener('keydown', handleKeyboardNavigation);
  }, []); // ✅ Empty deps - event listener added once, but always calls latest functions

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
    <SidebarProvider defaultOpen={false}>
      <div className="h-screen flex flex-col bg-background w-full">
        {/* Header */}
        <div className="border-b bg-white/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="px-3 md:px-6 py-2 md:py-4 flex items-center justify-between gap-2">
          {/* Left side - Navigation */}
          <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="flex items-center gap-1 md:gap-2 shrink-0"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden md:inline">Back</span>
            </Button>
            
            <div className="flex items-center gap-1 md:gap-2 min-w-0">
              <FileText className="h-4 w-4 md:h-5 md:w-5 text-primary shrink-0" />
              <h1 className="font-semibold text-sm md:text-lg truncate">
                {paper?.title || paper?.filename || 'Research Paper'}
              </h1>
            </div>
          </div>
          
          {/* Center - Page Navigation */}
          <div className="flex items-center gap-1 md:gap-4 shrink-0">
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
              className="h-8 w-8 md:h-9 md:w-9 p-0"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            
            <div className="flex items-center gap-1 md:gap-2">
              <span className="text-xs md:text-sm text-muted-foreground hidden sm:inline">Page</span>
              <form onSubmit={handlePageInputSubmit}>
                <Input
                  type="text"
                  value={pageInputValue}
                  onChange={handlePageInputChange}
                  className="w-10 md:w-16 h-7 md:h-8 text-center text-xs md:text-sm"
                  onBlur={handlePageInputSubmit}
                />
              </form>
              <span className="text-xs md:text-sm text-muted-foreground">/ {totalPages}</span>
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
              className="h-8 w-8 md:h-9 md:w-9 p-0"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Right side - Controls */}
          <div className="flex items-center gap-1 md:gap-2 shrink-0">
            {/* Font size controls - hide on mobile */}
            <div className="hidden lg:flex items-center gap-1">
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
            </div>
            
            {/* Actions - hide some on mobile */}
            <Button variant="ghost" size="sm" className="hidden md:flex">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="hidden md:flex">
              <Share2 className="h-4 w-4" />
            </Button>
            
            {/* Sidebar toggle - single button for all screen sizes */}
            <SidebarTrigger className="gap-1 md:gap-2">
              <Brain className="h-4 w-4" />
              <span className="hidden sm:inline text-xs md:text-sm">AI</span>
            </SidebarTrigger>
          </div>
        </div>
      </div>
      
      {/* Main Content Area with Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        <SidebarInset className="overflow-auto">
          <div 
            ref={contentRef}
            className="w-full max-w-4xl mx-auto px-2 py-3 sm:px-4 sm:py-4 md:p-8 pb-8 md:pb-16"
          >
            {/* Tabs for Paper Text and Multimodal Content */}
            <Tabs defaultValue="text" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="text" className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Paper Text
                </TabsTrigger>
                <TabsTrigger value="multimodal" className="flex items-center gap-2">
                  <ImageIcon className="h-4 w-4" />
                  Images & Tables
                </TabsTrigger>
              </TabsList>

              {/* Paper Text Tab */}
              <TabsContent value="text" className="space-y-4">
                {/* Page indicator */}
                <div className="mb-2 sm:mb-3 md:mb-4 text-center">
                  <span className="inline-flex items-center px-2 md:px-3 py-1 bg-primary/10 text-primary text-[10px] sm:text-xs md:text-sm rounded-full">
                    Page {optimisticPage} of {totalPages}
                  </span>
                </div>

                {/* Page content */}
                <motion.div
                  key={optimisticPage}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`prose prose-sm max-w-none ${getFontSizeClass()}`}
                >
                  <div className="min-h-[300px] sm:min-h-[400px] md:min-h-[600px] p-2 sm:p-3 md:p-6 bg-white rounded-lg shadow-sm border overflow-x-hidden">
                    <div className="wrap-break-word overflow-wrap-anywhere">
                      <FormattedContent content={currentPageData.content} />
                    </div>
                  </div>
                </motion.div>

                {/* Page navigation footer */}
                <div className="mt-3 sm:mt-4 md:mt-8 flex justify-between items-center gap-1 sm:gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const prevPage = Math.max(1, currentPage - 1);
                      startTransition(() => {
                        setOptimisticPage(prevPage);
                        goToPreviousPage();
                      });
                    }}
                    disabled={currentPage <= 1}
                    className="flex items-center gap-1 text-xs sm:text-sm px-2 sm:px-3"
                  >
                    <ChevronLeft className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span className="hidden xs:inline sm:hidden">Prev</span>
                    <span className="hidden sm:inline">Previous</span>
                  </Button>
                  
                  <span className="text-[10px] sm:text-xs md:text-sm text-muted-foreground">
                    {optimisticPage} / {totalPages}
                  </span>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const nextPage = Math.min(totalPages, currentPage + 1);
                      startTransition(() => {
                        setOptimisticPage(nextPage);
                        goToNextPage();
                      });
                    }}
                    disabled={currentPage >= totalPages}
                    className="flex items-center gap-1 text-xs sm:text-sm px-2 sm:px-3"
                  >
                    <span className="hidden xs:inline sm:hidden">Next</span>
                    <span className="hidden sm:inline">Next</span>
                    <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4" />
                  </Button>
                </div>
              </TabsContent>

              {/* Multimodal Content Tab */}
              <TabsContent value="multimodal" className="space-y-4">
                <MultiModalContent paperId={paper.paper_id} />
              </TabsContent>
            </Tabs>
          </div>
        </SidebarInset>
        
        {/* AI Insights Sidebar using shadcn Sidebar */}
        <Sidebar side="right" className="border-l">
          <SidebarHeader className="border-b">
            <div className="flex items-center justify-between p-4">
              <h2 className="font-semibold text-base lg:text-lg">AI Insights</h2>
              <SidebarTrigger className="h-8 w-8">
                <X className="h-4 w-4" />
              </SidebarTrigger>
            </div>
          </SidebarHeader>
          <SidebarContent className="p-4 space-y-4">
                {/* Sidebar sections */}
                {sidebarSections.map((section, index) => {
                  const IconComponent = section.icon;
                  
                  return (
                    <Card key={section.id}>
                      <CardHeader className="pb-3 p-3">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <IconComponent className="h-4 w-4" />
                          {section.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="text-xs text-gray-700 leading-relaxed p-3 pt-0">
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
          </SidebarContent>
        </Sidebar>
      </div>
      
      {/* Keyboard shortcuts help */}
      <div className="absolute bottom-4 left-4 text-xs text-muted-foreground bg-white/80 backdrop-blur-sm px-2 py-1 rounded hidden md:block">
        ← → Navigate • Ctrl+B Toggle sidebar
      </div>
    </div>
    </SidebarProvider>
  );
}