/**
 * Paper Detail Page
 * 
 * Displays individual paper with AI insights, interactive reader, and chat interface.
 */

'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { FileText, MessageCircle, Brain, Calendar, Clock, ArrowLeft, BookOpen } from 'lucide-react';
import { format } from 'date-fns';

import { usePaper } from '@/lib/react-query';
import { ProcessingStatus } from '@/components/ProcessingStatus';
import { PaperReader } from '@/components/reader/PaperReader';
import ChatInterface from '@/components/chat/ChatInterface.jsx';
import { FormattedContent } from '@/components/ui/formatted-content';

export default function PaperPage() {
  const params = useParams();
  const router = useRouter();
  const paperId = params.id;
  
  const { data: paper, isLoading, error } = usePaper(paperId);

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
    <div className="container mx-auto py-4 md:py-8 px-4 space-y-4 md:space-y-6">
      {/* Back Button */}
      <Button onClick={handleBack} variant="outline" size="sm">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Papers
      </Button>

      {/* Header */}
      <Card>
        <CardHeader className="p-4 md:p-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <CardTitle className="text-lg md:text-2xl">{paper.title}</CardTitle>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {format(new Date(paper.created_at), 'MMM d, yyyy')}
                </div>
                {paper.updated_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {format(new Date(paper.updated_at), 'h:mm a')}
                  </div>
                )}
              </div>
            </div>
            <ProcessingStatus paper={paper} />
          </div>
        </CardHeader>
      </Card>

      {/* Processing Banner - informational only, button is in header */}
      {(paper.processing_status === 'uploaded' || paper.processing_status === 'failed') && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <Brain className="h-5 w-5 text-blue-600" />
              <div>
                <h3 className="font-medium text-blue-900">AI Summary Available</h3>
                <p className="text-sm text-blue-700">Use the button above to generate AI insights for this paper</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="w-full grid grid-cols-4 h-auto">
          <TabsTrigger value="overview" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm">
            <FileText className="h-3 w-3 md:h-4 md:w-4 shrink-0" />
            <span className="hidden sm:inline">Overview</span>
            <span className="sm:hidden">Info</span>
          </TabsTrigger>
          <TabsTrigger value="content" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm">
            <Brain className="h-3 w-3 md:h-4 md:w-4 shrink-0" />
            <span className="hidden sm:inline">AI Analysis</span>
            <span className="sm:hidden">AI</span>
          </TabsTrigger>
          <TabsTrigger value="reader" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm">
            <BookOpen className="h-3 w-3 md:h-4 md:w-4 shrink-0" />
            <span className="hidden sm:inline">Reader</span>
            <span className="sm:hidden">Read</span>
          </TabsTrigger>
          <TabsTrigger value="chat" className="flex items-center justify-center gap-1 md:gap-2 text-xs md:text-sm">
            <MessageCircle className="h-3 w-3 md:h-4 md:w-4 shrink-0" />
            <span className="hidden sm:inline">Chat</span>
            <span className="sm:hidden">Chat</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader className="p-4 md:p-6">
              <CardTitle className="text-base md:text-lg">Document Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-4 md:p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Processing Status
                  </label>
                  <div className="mt-1">
                    <ProcessingStatus paper={paper} showButton={false} />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    File Size
                  </label>
                  <p className="mt-1">
                    {paper.file_size 
                      ? `${(paper.file_size / (1024 * 1024)).toFixed(2)} MB` 
                      : 'Unknown'
                    }
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Original Filename
                  </label>
                  <p className="mt-1 text-sm truncate" title={paper.filename}>
                    {paper.filename || 'Unknown'}
                  </p>
                </div>
              </div>
              
              {(paper.content || paper.content_text) && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Content Preview
                  </label>
                  <div className="mt-1 p-3 bg-muted rounded-lg max-h-64 overflow-y-auto">
                    <p className="text-sm whitespace-pre-wrap">
                      {(paper.content || paper.content_text)?.slice(0, 1000)}
                      {(paper.content || paper.content_text)?.length > 1000 && '...'}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="content" className="space-y-4">
          {paper.processing_status === 'completed' && paper.summary ? (
            <div className="grid gap-4">
              {/* Key Points */}
              <Card>
                <CardHeader className="p-4 md:p-6">
                  <CardTitle className="flex items-center gap-2 text-base md:text-lg">
                    <Brain className="h-4 w-4 md:h-5 md:w-5" />
                    Key Points
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 md:p-6">
                  {paper.summary.key_points && paper.summary.key_points.length > 0 ? (
                    <div className="space-y-4">
                      {paper.summary.key_points.map((point, index) => (
                        <div key={index} className="prose prose-sm max-w-none">
                          <FormattedContent content={point} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No key points extracted.</p>
                  )}
                </CardContent>
              </Card>

              {/* Citations */}
              {paper.summary.citations && paper.summary.citations.length > 0 && (
                <Card>
                  <CardHeader className="p-4 md:p-6">
                    <CardTitle className="text-base md:text-lg">Citations</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 md:p-6">
                    <div className="space-y-2">
                      {paper.summary.citations.map((citation, index) => (
                        <div key={index} className="text-sm bg-muted p-3 rounded prose prose-sm max-w-none">
                          <FormattedContent content={citation} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Related Works */}
              {paper.summary.related_works && paper.summary.related_works.length > 0 && (
                <Card>
                  <CardHeader className="p-4 md:p-6">
                    <CardTitle className="text-base md:text-lg">Related Works</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 md:p-6">
                    <div className="flex flex-wrap gap-2">
                      {paper.summary.related_works.map((work, index) => (
                        <Badge key={index} variant="secondary">
                          {work}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card className="text-center py-12">
              <Brain className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">AI Analysis Not Available</h3>
              <p className="text-muted-foreground mb-4">
                This document hasn&apos;t been processed by AI yet.
              </p>
              <ProcessingStatus paper={paper} />
            </Card>
          )}
        </TabsContent>

        <TabsContent value="reader" className="space-y-4">
          <div className="h-[calc(100vh-14rem)] sm:h-[calc(100vh-16rem)] md:h-[800px] min-h-[350px] sm:min-h-[400px] rounded-lg border overflow-hidden">
            <PaperReader 
              paper={paper} 
              onBack={handleBack} 
            />
          </div>
        </TabsContent>

        <TabsContent value="chat" className="space-y-4">
          <div className="h-[calc(100vh-12rem)] md:h-[600px] lg:h-[700px] min-h-[450px]">
            <ChatInterface paper={paper} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}