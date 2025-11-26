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
    <div className="container mx-auto py-8 space-y-6">
      {/* Back Button */}
      <Button onClick={handleBack} variant="outline" size="sm">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Papers
      </Button>

      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <CardTitle className="text-2xl">{paper.title}</CardTitle>
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

      {/* Processing Banner */}
      {(paper.processing_status === 'uploaded' || paper.processing_status === 'failed') && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-blue-900">AI Summary Available</h3>
                <p className="text-sm text-blue-700">Generate AI insights for this paper</p>
              </div>
              <ProcessingStatus 
                paper={paper}
                showButton={true}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="content" className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            AI Analysis
          </TabsTrigger>
          <TabsTrigger value="reader" className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Reader
          </TabsTrigger>
          <TabsTrigger value="chat" className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4" />
            Chat
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Document Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
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
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5" />
                    Key Points
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {paper.summary.key_points && paper.summary.key_points.length > 0 ? (
                    <ul className="space-y-2">
                      {paper.summary.key_points.map((point, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="w-2 h-2 bg-primary rounded-full mt-2 shrink-0" />
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted-foreground">No key points extracted.</p>
                  )}
                </CardContent>
              </Card>

              {/* Citations */}
              {paper.summary.citations && paper.summary.citations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Citations</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {paper.summary.citations.map((citation, index) => (
                        <li key={index} className="text-sm bg-muted p-3 rounded">
                          {citation}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Related Works */}
              {paper.summary.related_works && paper.summary.related_works.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Related Works</CardTitle>
                  </CardHeader>
                  <CardContent>
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
          <div className="h-[800px] rounded-lg border overflow-hidden">
            <PaperReader 
              paper={paper} 
              onBack={handleBack} 
            />
          </div>
        </TabsContent>

        <TabsContent value="chat" className="space-y-4">
          <div className="min-h-[600px]">
            <ChatInterface paper={paper} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}