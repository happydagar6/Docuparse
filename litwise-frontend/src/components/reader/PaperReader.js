/**
 * Enhanced Paper Reader Component with Pagination
 * 
 * Features:
 * - PDF-style pagination with page navigation
 * - Responsive sidebar with AI insights
 * - Robust error handling and loading states
 * - Responsive design with keyboard shortcuts
 * - Page-based content display
 * - Mobile-optimized controls
 * - Smooth animations and transitions
 * - Advanced tab interface for text, images, and citations
 */

'use client';

import { useState, useRef, useLayoutEffect, useCallback, useMemo } from 'react';
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
  Loader2,
  MoreVertical,
  Eye,
  Copy,
  Menu,
  Lightbulb,
  Sparkles,
  Quote,
  Users,
  Calendar
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FormattedContent, FormattedSummary } from '@/components/ui/formatted-content';
import { usePaperStore } from '@/lib/stores';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import MultiModalContent from './MultiModalContent';
import PaperPDFViewer from './PaperPDFViewer';
import { Image as ImageIcon } from 'lucide-react';
import CitationList from '@/components/citations/CitationList';
import CitationStats from '@/components/citations/CitationStats';
import CitationControls from '@/components/citations/CitationControls';
import CitationButton from '@/components/citations/CitationButton';
import { getPaperCitations, getCitationStats } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

export function PaperReader({ paper, onBack }) {
  // Local state
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pageInputValue, setPageInputValue] = useState('');
  const [citations, setCitations] = useState([]);
  const [citationStats, setCitationStats] = useState(null);
  const [citationsLoading, setCitationsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('text');
  
  // Refs
  const contentRef = useRef(null);
  const sidebarRef = useRef(null);
  
  // Zustand store for paper reader state
  const {
    showSidebar,
    fontSize,
    theme,
    highlightedSections,
    toggleSidebar,
    setCurrentPage,
    setFontSize,
    clearHighlights
  } = usePaperStore();

  /**
   * Validate paper content when data loads
   * NOTE: Pagination is now handled entirely by PaperPDFViewer and AdvancedPDFViewer
   * This initialization just validates the content exists
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

        // Content validation passed - PaperPDFViewer will handle pagination
        setPageInputValue('1');

      } catch (err) {
        console.error('Error loading paper:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
  }, [paper]);

  // React 19.2: Initialize with useLayoutEffect for synchronous updates
  useLayoutEffect(() => {
    if (paperInitialization) {
      paperInitialization();
    }

    // Cleanup on unmount
    return () => {
      // Pagination is now managed by PaperPDFViewer component
    };
  }, [paperInitialization]);

  /**
   * Load citations for the paper
   */
  const loadCitations = useCallback(async () => {
    if (!paper?.id) return;
    
    setCitationsLoading(true);
    try {
      const [citationsData, statsData] = await Promise.all([
        getPaperCitations(paper.id),
        getCitationStats(paper.id)
      ]);
      setCitations(citationsData);
      setCitationStats(statsData);
    } catch (error) {
      console.error('Failed to load citations:', error);
    } finally {
      setCitationsLoading(false);
    }
  }, [paper?.id]);

  // Load citations when paper changes
  useLayoutEffect(() => {
    loadCitations();
  }, [loadCitations]);

  /**
   * Handle page input change (for future use with PaperPDFViewer)
   */
  const handlePageInputChange = (e) => {
    const value = e.target.value;
    setPageInputValue(value);
  };

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
      case 'small': return 'text-sm leading-relaxed';
      case 'large': return 'text-lg leading-relaxed';
      default: return 'text-base leading-relaxed';
    }
  };

  /**
   * Sidebar content sections
   */
  const sidebarSections = [
    {
      id: 'summary',
      title: 'AI Summary',
      icon: Sparkles,
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
      <div className="h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-muted-foreground">Loading paper...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-white">
        <Card className="p-6 max-w-md border-red-200 bg-red-50">
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
    <div className="h-full w-full bg-white flex flex-col">
      {/* Enhanced Header */}
      <motion.div 
        className="border-b bg-linear-to-r from-white via-slate-50 to-white/80 backdrop-blur-sm sticky top-0 z-20 shadow-sm"
        initial={{ y: -10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="px-2 sm:px-4 md:px-6 py-2.5 md:py-3 flex items-center justify-between gap-2">
          {/* Left side - Back Button & Title */}
          <div className="flex items-center gap-1.5 md:gap-3 flex-1 min-w-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="shrink-0 hover:bg-slate-100 h-8 w-8 md:h-9 md:w-9"
              title="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            
            <div className="flex items-center gap-1.5 md:gap-2 min-w-0">
              <div className="flex items-center justify-center w-7 h-7 md:w-8 md:h-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 shrink-0">
                <FileText className="h-3.5 w-3.5 md:h-4 md:w-4 text-white" />
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="font-semibold text-xs sm:text-sm md:text-base truncate text-slate-900 block">
                  {paper?.title || paper?.filename || 'Research Paper'}
                </h1>
              </div>
            </div>
          </div>
          
          {/* Center - Note: Page navigation now handled by AdvancedPDFViewer in the Text tab */}
          
          {/* Right side - Controls */}
          <div className="flex items-center gap-0.5 md:gap-1 shrink-0">
            {/* Font size controls - hide on mobile */}
            <div className="hidden sm:flex items-center gap-0 bg-slate-100/60 rounded-full px-1 py-1 border border-slate-200/50">
              <Button
                variant="ghost"
                size="sm"
                onClick={decreaseFontSize}
                disabled={fontSize === 'small'}
                className="h-7 w-7 p-0 rounded hover:bg-white transition-colors"
                title="Decrease font size"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={increaseFontSize}
                disabled={fontSize === 'large'}
                className="h-7 w-7 p-0 rounded hover:bg-white transition-colors"
                title="Increase font size"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </Button>
            </div>
            
            {/* More Actions Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 md:h-9 md:w-9 p-0 rounded hover:bg-slate-100 transition-colors">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Reader Options</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Share2 className="mr-2 h-4 w-4" />
                  Share Paper
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy Link
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            {/* Sidebar toggle button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebar}
              className="h-8 w-8 md:h-9 md:w-9 p-0 rounded hover:bg-slate-100 transition-colors flex items-center justify-center"
              title="Toggle AI Insights"
            >
              <Brain className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </motion.div>
      
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden gap-0">
        {/* Main Content */}
        <div className="flex-1 overflow-hidden flex flex-col bg-white">
          <div 
            ref={contentRef}
            className="w-full h-full flex flex-col overflow-hidden"
          >
          {/* Tabs for Paper Text and Multimodal Content */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full h-full flex flex-col overflow-hidden">
              <div className="border-b bg-white sticky top-0 z-10">
                <div className="px-2 sm:px-4 md:px-6 py-2 md:py-3">
                  <TabsList className="grid grid-cols-3 w-full md:w-auto md:inline-flex h-auto bg-slate-100/60 p-1 rounded-lg border border-slate-200/50">
                    <TabsTrigger 
                      value="text"
                      className="flex items-center justify-center gap-1 px-2 sm:px-3 md:px-4 py-2 text-xs sm:text-sm data-[state=active]:bg-white data-[state=active]:shadow-sm rounded transition-all"
                    >
                      <FileText className="h-3.5 w-3.5 md:h-4 md:w-4" />
                      <span className="hidden sm:inline">Text</span>
                      <span className="sm:hidden">Read</span>
                    </TabsTrigger>
                    
                    <TabsTrigger 
                      value="multimodal"
                      className="flex items-center justify-center gap-1 px-2 sm:px-3 md:px-4 py-2 text-xs sm:text-sm data-[state=active]:bg-white data-[state=active]:shadow-sm rounded transition-all"
                    >
                      <ImageIcon className="h-3.5 w-3.5 md:h-4 md:w-4" />
                      <span className="hidden sm:inline">Media</span>
                      <span className="sm:hidden">Media</span>
                    </TabsTrigger>
                    
                    <TabsTrigger 
                      value="citations"
                      className="flex items-center justify-center gap-1 px-2 sm:px-3 md:px-4 py-2 text-xs sm:text-sm data-[state=active]:bg-white data-[state=active]:shadow-sm rounded transition-all relative"
                    >
                      <BookOpen className="h-3.5 w-3.5 md:h-4 md:w-4" />
                      <span className="hidden sm:inline">Cite</span>
                      <span className="sm:hidden">Cite</span>
                      {citations.length > 0 && (
                        <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0 h-5 flex items-center justify-center min-w-max">
                          {citations.length}
                        </Badge>
                      )}
                    </TabsTrigger>
                  </TabsList>
                </div>
              </div>

              {/* Tab Contents */}
              <div className="flex-1 overflow-hidden">
                {/* Paper Text Tab - Using new PDF Viewer */}
                <TabsContent value="text" className="h-full flex flex-col m-0 overflow-hidden">
                  <PaperPDFViewer
                    paper={paper}
                    isLoading={isLoading}
                    error={error}
                    onDownload={() => {
                      // Optional: Implement PDF download functionality
                      console.log('Download PDF:', paper.title);
                    }}
                  />
                </TabsContent>

                {/* Multimodal Content Tab */}
                <TabsContent value="multimodal" className="h-full flex flex-col m-0 overflow-hidden">
                  <div className="flex-1 overflow-y-auto p-2 sm:p-4 md:p-6">
                    <div className="max-w-6xl mx-auto">
                      <MultiModalContent paperId={paper.id} />
                    </div>
                  </div>
                </TabsContent>

                {/* Citations Tab */}
                <TabsContent value="citations" className="h-full flex flex-col m-0 overflow-hidden">
                  <div className="flex-1 overflow-y-auto p-2 sm:p-4 md:p-6">
                    <div className="max-w-5xl mx-auto space-y-8">
                      {/* Cite This Paper Section */}
                      <div>
                        <div className="mb-4">
                          <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-slate-900 mb-2 flex items-center gap-2">
                            <Quote className="h-5 w-5 md:h-6 md:w-6 text-blue-600" />
                            Cite This Paper
                          </h2>
                          <p className="text-slate-600 text-xs sm:text-sm md:text-base">
                            Generate formatted citation for this paper using AI-extracted metadata
                          </p>
                        </div>
                        
                        <Card className="border-blue-200 bg-blue-50/30">
                          <CardContent className="p-4 sm:p-6">
                            <div className="flex items-start gap-4">
                              <div className="shrink-0">
                                <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center">
                                  <Sparkles className="h-5 w-5 text-white" />
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-slate-900 mb-2 text-sm sm:text-base">
                                  {paper.title}
                                </h3>
                                {paper.authors && paper.authors.length > 0 && (
                                  <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-600 mb-2">
                                    <Users className="h-4 w-4 shrink-0" />
                                    <span>
                                      {paper.authors.map(a => a.name || a).slice(0, 3).join(', ')}
                                      {paper.authors.length > 3 && ` et al.`}
                                    </span>
                                  </div>
                                )}
                                {paper.publication_year && (
                                  <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-600 mb-2">
                                    <Calendar className="h-4 w-4 shrink-0" />
                                    <span>{paper.publication_year}</span>
                                  </div>
                                )}
                                {paper.doi && (
                                  <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-600 mb-4">
                                    <Link2 className="h-4 w-4 shrink-0" />
                                    <a 
                                      href={`https://doi.org/${paper.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline truncate"
                                    >
                                      {paper.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}
                                    </a>
                                  </div>
                                )}
                                <div className="pt-2">
                                  <CitationButton
                                    paperId={paper.id}
                                    variant="default"
                                    size="default"
                                  />
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                      
                      {/* References FROM the Paper */}
                      <div>
                        <div className="mb-4">
                          <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-slate-900 mb-2 flex items-center gap-2">
                            <BookOpen className="h-5 w-5 md:h-6 md:w-6 text-blue-600" />
                            References in This Paper
                          </h2>
                          <p className="text-slate-600 text-xs sm:text-sm md:text-base">
                            Auto-extracted citations from the bibliography section
                          </p>
                        </div>
                        
                        <CitationStats stats={citationStats} isLoading={citationsLoading} />
                        
                        <CitationControls 
                          paperId={paper?.id} 
                          onRefresh={loadCitations}
                        />
                        
                        <CitationList
                          paperId={paper?.id}
                          citations={citations}
                          isLoading={citationsLoading}
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>
        
        {/* AI Insights Sidebar - Right Side */}
        <motion.div
          initial={{ x: 320, opacity: 0 }}
          animate={{ x: showSidebar ? 0 : 320, opacity: showSidebar ? 1 : 0 }}
          transition={{ duration: 0.3 }}
          className={`w-80 border-l border-slate-200/50 bg-linear-to-b from-slate-50 to-white flex flex-col shrink-0 overflow-hidden ${
            showSidebar ? 'visible' : 'hidden'
          }`}
        >
          {/* Sidebar Header */}
          <div className="border-b border-slate-200/50 bg-linear-to-r from-blue-50 to-cyan-50 p-4 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 shrink-0">
                  <Lightbulb className="h-4 w-4 text-white" />
                </div>
                <h2 className="font-semibold text-sm text-slate-900 truncate">AI Insights</h2>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className="h-8 w-8 p-0 hover:bg-white rounded transition-colors flex items-center justify-center shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* Sidebar Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Sidebar sections with enhanced styling */}
            {sidebarSections.map((section, index) => {
              const IconComponent = section.icon;
              
              return (
                <motion.div
                  key={section.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className="border-slate-200/50 overflow-hidden hover:shadow-md transition-all hover:border-slate-300/75">
                    <CardHeader className="pb-2 p-3 bg-linear-to-r from-slate-50 to-slate-50/50 border-b border-slate-200/30">
                      <CardTitle className="flex items-center gap-2 text-xs text-slate-900">
                        <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-linear-to-br from-blue-100 to-cyan-100 shrink-0">
                          <IconComponent className="h-3.5 w-3.5 text-blue-600" />
                        </div>
                        <span className="truncate text-xs font-semibold">{section.title}</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-slate-700 leading-relaxed p-3">
                      {section.content ? (
                        <div className="prose prose-sm max-w-none text-xs whitespace-pre-wrap">
                          {section.id === 'summary' ? (
                            <FormattedSummary summary={section.content} />
                          ) : Array.isArray(section.content) ? (
                            section.content.map((item, idx) => (
                              <div key={idx} className="py-1">
                                <span className="text-slate-700">{item}</span>
                              </div>
                            ))
                          ) : typeof section.content === 'string' && section.content.includes('•') ? (
                            <div className="space-y-1 whitespace-pre-line">
                              {section.content.split('\n').filter(line => line.trim()).map((line, idx) => (
                                <div key={idx} className="text-slate-700">
                                  {line}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <FormattedContent content={section.content} />
                          )}
                        </div>
                      ) : (
                        <p className="text-slate-500 italic text-xs">{section.title} will be generated.</p>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
            
            {/* Actions */}
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="space-y-2 pt-4 border-t border-slate-200 mt-4"
            >
              <Button 
                variant="outline" 
                size="sm" 
                onClick={clearHighlights}
                className="w-full text-xs hover:bg-red-50 transition-colors"
              >
                <X className="h-3 w-3 mr-1.5" />
                Clear Highlights
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setCurrentPage(1)}
                className="w-full text-xs hover:bg-blue-50 transition-colors"
              >
                <ChevronLeft className="h-3 w-3 mr-1.5" />
                First Page
              </Button>
            </motion.div>
          </div>
        </motion.div>
      </div>
      
    </div>
  );
}
