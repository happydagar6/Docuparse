/**
 * Individual Synthesis Detail Page
 * 
 * View full details of a saved synthesis with export options.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Loader2, 
  AlertCircle, 
  ArrowLeft,
  Calendar,
  FileText,
  Tag
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageLayout } from '@/components/layout/Layout';
import { getSynthesisById } from '@/lib/api';
import { SynthesisPanel } from '@/components/search/SynthesisPanel';
import { toast } from 'sonner';

export default function SynthesisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [synthesis, setSynthesis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const loadSynthesis = useCallback(async () => {
    if (!params.id) return;
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await getSynthesisById(params.id);
      
      // Transform data to match SynthesisPanel expected format
      const transformedSynthesis = {
        query: data.query,
        paper_count: data.paper_count,
        themes: data.themes,
        key_findings: data.key_findings,
        research_gaps: data.research_gaps,
        trends: data.trends,
        top_papers: data.top_papers,
        generated_at: data.created_at
      };
      
      setSynthesis({
        ...transformedSynthesis,
        metadata: {
          id: data.id,
          created_at: data.created_at,
          tags: data.tags || []
        }
      });
    } catch (err) {
      setError(err.message);
      toast.error('Failed to load synthesis', {
        description: err.message
      });
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);
  
  useEffect(() => {
    loadSynthesis();
  }, [loadSynthesis]);
  
  return (
    <PageLayout
      title="Synthesis Details"
      description="View saved research synthesis"
    >
      <div className="w-full max-w-4xl mx-auto space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => router.push('/synthesis')}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to History
        </Button>
        
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
                  <p className="text-sm font-medium text-red-800">Failed to load synthesis</p>
                  <p className="text-sm text-red-600">{error}</p>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={loadSynthesis}
                  className="ml-auto"
                >
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Synthesis Display */}
        {!isLoading && !error && synthesis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Metadata Card */}
            <Card className="mb-6">
              <CardHeader className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-xs sm:text-sm text-gray-500 mb-2">
                      Synthesis Information
                    </CardTitle>
                    <div className="space-y-2 text-xs sm:text-sm">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-3 w-3 sm:h-4 sm:w-4 text-gray-400 shrink-0" />
                        <span className="text-gray-600">
                          Saved on {new Date(synthesis.metadata.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <FileText className="h-3 w-3 sm:h-4 sm:w-4 text-gray-400 shrink-0" />
                        <span className="text-gray-600">
                          {synthesis.paper_count} papers analyzed
                        </span>
                      </div>
                    </div>
                  </div>
                  {synthesis.metadata.tags && synthesis.metadata.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 shrink-0">
                      {synthesis.metadata.tags.map((tag, i) => (
                        <Badge key={i} variant="secondary">
                          <Tag className="h-3 w-3 mr-1" />
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </CardHeader>
            </Card>
            
            {/* Synthesis Content */}
            <SynthesisPanel
              synthesis={synthesis}
              isLoading={false}
              error={null}
              searchResults={[]}
              maxPapers={synthesis.paper_count}
              savedSynthesisId={synthesis.metadata.id}
            />
          </motion.div>
        )}
      </div>
    </PageLayout>
  );
}
