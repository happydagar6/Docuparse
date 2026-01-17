/**
 * Paper Detail Page
 * 
 * Displays individual paper with AI insights, interactive reader, and chat interface.
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, MessageCircle, Brain, Calendar, Clock, ArrowLeft, BookOpen, Link2, Sparkles, Users, Hash, Tag, Building2 } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { usePaper } from '@/lib/react-query';
import { ProcessingStatus } from '@/components/ProcessingStatus';
import { PaperReader } from '@/components/reader/PaperReader';
import ChatInterface from '@/components/chat/ChatInterface.jsx';
import { FormattedContent } from '@/components/ui/formatted-content';
import SearchResultsPanel from '@/components/reader/SearchResultsPanel';

export default function PaperPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const paperId = params.id;
  
  // Get search context from URL params (chunk to scroll to, page to jump to, text to highlight)
  const chunkId = searchParams?.get('chunk_id');
  const pageNum = searchParams?.get('page');
  const highlightText = searchParams?.get('highlight');
  const tabParam = searchParams?.get('tab');
  const fromSearch = !!(chunkId || pageNum);
  
  // State for which tab to display (default to reader if coming from search, or specified tab)
  const activeTab = useMemo(() => {
    if (tabParam) return tabParam;
    if (fromSearch) return 'reader';
    return 'overview';
  }, [tabParam, fromSearch]);
  
  const { data: paper, isLoading, error } = usePaper(paperId);

  // Handle tab changes by updating URL
  const handleTabChange = (newTab) => {
    const newSearchParams = new URLSearchParams(searchParams);
    newSearchParams.set('tab', newTab);
    router.replace(`/papers/${paperId}?${newSearchParams.toString()}`, { scroll: false });
  };

  // Scroll to chunk when paper loads and search context is available
  useEffect(() => {
    if (!isLoading && paper && chunkId && typeof window !== 'undefined') {
      // Try to find and scroll to the element with matching chunk_id
      const chunkElement = document.getElementById(`chunk-${chunkId}`) || 
                          document.querySelector(`[data-chunk-id="${chunkId}"]`);
      
      if (chunkElement) {
        console.log('[PaperPage] Found chunk element, scrolling to:', chunkId);
        // Scroll with smooth animation and offset for header
        setTimeout(() => {
          chunkElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Highlight the element briefly
          chunkElement.style.backgroundColor = '#fff3cd'; // Yellow highlight
          setTimeout(() => {
            chunkElement.style.backgroundColor = '';
          }, 3000);
        }, 100);
        
        // Show toast notification
        toast.success(`Jumped to section from search result`);
      } else if (pageNum) {
        console.log('[PaperPage] No chunk found, scrolling to page:', pageNum);
        // Scroll to page number if available
        const pageElements = document.querySelectorAll('[data-page]');
        const targetPage = pageElements[parseInt(pageNum) - 1];
        if (targetPage) {
          targetPage.scrollIntoView({ behavior: 'smooth' });
        }
      }
    }
  }, [isLoading, paper, chunkId, pageNum]);

  const handleBack = () => {
    router.back();
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded"></div>
          <div className="h-4 bg-muted rounded w-3/4"></div>
          <div className="h-32 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !paper) {
    console.error('[PaperPage] Error loading paper:', error);
    return (
      <div className="container mx-auto py-8">
        <Card className="p-6 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">Paper Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The paper you&apos;re looking for doesn&apos;t exist or has been removed.
          </p>
          <Button onClick={handleBack} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-b from-white via-slate-50 to-white">
      <div className="container mx-auto py-4 md:py-6 px-3 sm:px-4 md:px-6 space-y-4 md:space-y-6">
      {/* Back Button */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Button onClick={handleBack} variant="ghost" size="sm" className="hover:bg-slate-100">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Papers
        </Button>
      </motion.div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
      >
        <Card className="border-slate-200/60 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="p-4 md:p-6">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-3 flex-1 min-w-0">
                <CardTitle className="text-lg sm:text-xl md:text-3xl text-slate-900 wrap-break-word">
                  {paper.title}
                </CardTitle>
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-blue-600" />
                    <span>{format(new Date(paper.created_at), 'MMM d, yyyy')}</span>
                  </div>
                  {paper.updated_at && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-blue-600" />
                      <span>{format(new Date(paper.updated_at), 'h:mm a')}</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <ProcessingStatus paper={paper} />
              </div>
            </div>
          </CardHeader>
        </Card>
      </motion.div>

      {/* Processing Banner - informational only, button is in header */}
      <AnimatePresence>
        {(paper.processing_status === 'uploaded' || paper.processing_status === 'failed') && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="bg-linear-to-r from-blue-50 to-cyan-50 border-blue-200/60">
              <CardContent className="py-4 px-4 md:px-6">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-blue-900 text-sm md:text-base">AI Analysis Available</h3>
                    <p className="text-xs md:text-sm text-blue-700 mt-1">Use the button above to generate AI insights for this paper</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
          <div className="bg-white border-b border-slate-200/50 rounded-t-lg p-1 md:p-2">
            <TabsList className="w-full grid grid-cols-2 md:grid-cols-4 h-auto bg-slate-100/50 p-1 rounded-lg border border-slate-200/50">
              <TabsTrigger value="overview" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm py-2 md:py-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm rounded">
                <FileText className="h-3.5 w-3.5 md:h-4 md:w-4 shrink-0" />
                <span className="hidden sm:inline">Overview</span>
                <span className="sm:hidden">Info</span>
              </TabsTrigger>
              <TabsTrigger value="content" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm py-2 md:py-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm rounded">
                <Brain className="h-3.5 w-3.5 md:h-4 md:w-4 shrink-0" />
                <span className="hidden sm:inline">AI Analysis</span>
                <span className="sm:hidden">AI</span>
              </TabsTrigger>
              <TabsTrigger value="reader" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm py-2 md:py-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm rounded">
                <BookOpen className="h-3.5 w-3.5 md:h-4 md:w-4 shrink-0" />
                <span className="hidden sm:inline">Reader</span>
                <span className="sm:hidden">Read</span>
              </TabsTrigger>
              <TabsTrigger value="chat" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm py-2 md:py-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm rounded">
                <MessageCircle className="h-3.5 w-3.5 md:h-4 md:w-4 shrink-0" />
                <span className="hidden sm:inline">Chat</span>
                <span className="sm:hidden">Chat</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="overview" className="space-y-4 mt-0">
            {/* Abstract Section - Prominent Display */}
            {paper.abstract && (
              <Card className="border-blue-200/60 bg-linear-to-br from-blue-50/30 to-cyan-50/30">
                <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                  <CardTitle className="text-base md:text-lg flex items-center gap-2 text-slate-900">
                    <FileText className="h-5 w-5 text-blue-600" />
                    Abstract
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 md:p-6 pt-0">
                  <div className="prose prose-sm md:prose-base max-w-none">
                    <p className="text-sm md:text-base text-slate-700 leading-relaxed whitespace-pre-wrap">
                      {paper.abstract}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Research Metadata */}
            {(paper.authors || paper.publication_year || paper.doi || paper.journal_or_conference || paper.keywords) && (
              <Card className="border-slate-200/60">
                <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                  <CardTitle className="text-base md:text-lg flex items-center gap-2 text-slate-900">
                    <Brain className="h-5 w-5 text-blue-600" />
                    Research Metadata
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 p-4 md:p-6 pt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Authors */}
                    {paper.authors && paper.authors.length > 0 && (
                      <div className="space-y-2">
                        <label className="text-xs md:text-sm font-semibold text-muted-foreground flex items-center gap-2">
                          <Users className="h-4 w-4 text-blue-600" />
                          Authors
                        </label>
                        <div className="flex flex-wrap gap-2">
                          {paper.authors.map((author, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs md:text-sm bg-blue-50 text-blue-700 border-blue-200">
                              {typeof author === 'string' ? author : author.name}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Publication Year & Venue */}
                    <div className="space-y-3">
                      {paper.publication_year && (
                        <div className="space-y-2">
                          <label className="text-xs md:text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-blue-600" />
                            Publication Year
                          </label>
                          <Badge variant="outline" className="text-xs md:text-sm bg-slate-50 text-slate-700 border-slate-300">
                            {paper.publication_year}
                          </Badge>
                        </div>
                      )}
                      
                      {paper.journal_or_conference && (
                        <div className="space-y-2">
                          <label className="text-xs md:text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <Building2 className="h-4 w-4 text-blue-600" />
                            Published In
                          </label>
                          <Badge variant="outline" className="text-xs md:text-sm bg-purple-50 text-purple-700 border-purple-200">
                            {paper.journal_or_conference}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* DOI */}
                  {paper.doi && (
                    <div className="space-y-2">
                      <label className="text-xs md:text-sm font-semibold text-muted-foreground flex items-center gap-2">
                        <Link2 className="h-4 w-4 text-blue-600" />
                        DOI
                      </label>
                      <a 
                        href={`https://doi.org/${paper.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm md:text-base text-blue-600 hover:text-blue-800 hover:underline font-mono bg-blue-50 px-3 py-1.5 rounded border border-blue-200 transition-colors"
                      >
                        {paper.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}
                        <Link2 className="h-3 w-3" />
                      </a>
                    </div>
                  )}

                  {/* Keywords */}
                  {paper.keywords && paper.keywords.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-slate-200/50">
                      <label className="text-xs md:text-sm font-semibold text-muted-foreground flex items-center gap-2">
                        <Tag className="h-4 w-4 text-blue-600" />
                        Keywords
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {paper.keywords.map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs md:text-sm bg-slate-100 text-slate-700">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Document Information */}
            <Card className="border-slate-200/60">
              <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                <CardTitle className="text-base md:text-lg flex items-center gap-2 text-slate-900">
                  <FileText className="h-5 w-5 text-blue-600" />
                  Document Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 p-4 md:p-6 pt-0">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs md:text-sm font-semibold text-muted-foreground block">
                      Processing Status
                    </label>
                    <div>
                      <ProcessingStatus paper={paper} showButton={false} />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs md:text-sm font-semibold text-muted-foreground block">
                      File Size
                    </label>
                    <p className="text-sm md:text-base text-slate-900 font-medium">
                      {paper.file_size 
                        ? `${(paper.file_size / (1024 * 1024)).toFixed(2)} MB` 
                        : 'Unknown'
                      }
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs md:text-sm font-semibold text-muted-foreground block">
                      Filename
                    </label>
                    <p className="text-sm md:text-base text-slate-900 font-medium truncate" title={paper.filename}>
                      {paper.filename || 'Unknown'}
                    </p>
                  </div>
                </div>
                
                {(paper.content || paper.content_text) && (
                  <div className="space-y-2 pt-2 border-t border-slate-200/50">
                    <label className="text-xs md:text-sm font-semibold text-muted-foreground block">
                      Content Preview
                    </label>
                    <div className="p-3 md:p-4 bg-slate-50 rounded-lg max-h-48 md:max-h-64 overflow-y-auto border border-slate-200/50">
                      <p className="text-xs md:text-sm whitespace-pre-wrap text-slate-700 leading-relaxed">
                        {(paper.content || paper.content_text)?.slice(0, 1000)}
                        {(paper.content || paper.content_text)?.length > 1000 && '...'}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="content" className="space-y-4 mt-0">
            {paper.processing_status === 'completed' && paper.summary ? (
              <div className="space-y-4">
                {/* Key Points */}
                <Card className="border-slate-200/60 overflow-hidden hover:shadow-md transition-shadow">
                  <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                    <CardTitle className="flex items-center gap-2 text-base md:text-lg text-slate-900">
                      <Sparkles className="h-5 w-5 md:h-6 md:w-6 text-blue-600" />
                      Key Points
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 md:p-6 pt-0 space-y-3">
                    {paper.summary.key_points && paper.summary.key_points.length > 0 ? (
                      <div className="space-y-3">
                        {paper.summary.key_points.map((point, index) => (
                          <div key={index} className="prose prose-sm max-w-none text-xs md:text-sm bg-slate-50 p-3 rounded-lg border border-slate-200/30">
                            <div className="flex gap-2">
                              <span className="text-blue-600 font-bold shrink-0">·</span>
                              <div className="flex-1">
                                <FormattedContent content={point} />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted-foreground text-sm italic">No key points extracted.</p>
                    )}
                  </CardContent>
                </Card>

                {/* Citations */}
                {paper.summary.citations && paper.summary.citations.length > 0 && (
                  <Card className="border-slate-200/60 overflow-hidden hover:shadow-md transition-shadow">
                    <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                      <CardTitle className="flex items-center gap-2 text-base md:text-lg text-slate-900">
                        <BookOpen className="h-5 w-5 md:h-6 md:w-6 text-blue-600" />
                        Related Citations
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 md:p-6 pt-0">
                      <div className="space-y-2">
                        {paper.summary.citations.map((citation, index) => (
                          <div key={index} className="text-xs md:text-sm bg-slate-50 p-3 rounded-lg prose prose-sm max-w-none border border-slate-200/30">
                            <FormattedContent content={citation} />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Related Works */}
                {paper.summary.related_works && paper.summary.related_works.length > 0 && (
                  <Card className="border-slate-200/60 overflow-hidden hover:shadow-md transition-shadow">
                    <CardHeader className="p-4 md:p-6 pb-3 md:pb-4">
                      <CardTitle className="flex items-center gap-2 text-base md:text-lg text-slate-900">
                        <Link2 className="h-5 w-5 md:h-6 md:w-6 text-blue-600" />
                        Related Works
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 md:p-6 pt-0">
                      <div className="flex flex-wrap gap-2">
                        {paper.summary.related_works.map((work, index) => (
                          <Badge key={index} variant="secondary" className="text-xs md:text-sm">
                            {work}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              <Card className="border-slate-200/60 text-center py-12 md:py-16">
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <Brain className="h-12 w-12 md:h-16 md:w-16 text-muted-foreground/50" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-base md:text-lg font-semibold text-slate-900">AI Analysis Not Available</h3>
                    <p className="text-xs md:text-sm text-muted-foreground">
                      This document hasn&apos;t been processed by AI yet.
                    </p>
                  </div>
                  <div>
                    <ProcessingStatus paper={paper} />
                  </div>
                </div>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="reader" className="space-y-4 mt-0">
            {/* Search Results Panel - show when coming from search */}
            {fromSearch && showSearchPanel && (
              <SearchResultsPanel 
                searchContext={{
                  chunk_id: chunkId,
                  page: pageNum,
                  content: highlightText,
                  title: paper?.title
                }}
                paper={paper}
                onClose={() => setShowSearchPanel(false)}
              />
            )}
            
            <div className="h-[calc(100vh-12rem)] sm:h-[calc(100vh-14rem)] md:h-[800px] min-h-[350px] sm:min-h-[400px] rounded-lg border border-slate-200/60 overflow-hidden bg-white shadow-sm">
              <PaperReader 
                paper={paper} 
                onBack={handleBack} 
              />
            </div>
          </TabsContent>

          <TabsContent value="chat" className="space-y-4 mt-0">
            <div className="h-[calc(100vh-12rem)] md:h-[600px] lg:h-[700px] min-h-[450px] rounded-lg border border-slate-200/60 overflow-hidden bg-white shadow-sm">
              <ChatInterface paper={paper} />
            </div>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
    </div>
  );
}