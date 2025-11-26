/**
 * Papers List Page
 * 
 * Browse and manage uploaded research papers.
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Search, 
  Calendar,
  Filter,
  Grid,
  List,
  MoreVertical,
  Eye,
  Download,
  Trash2,
  Upload
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormattedSummary } from '@/components/ui/formatted-content';
import { ProcessingBadge, ProcessingStatus } from '@/components/ProcessingStatus';
import { Skeleton } from '@/components/ui/skeleton';
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
import { usePapers, useDeletePaper } from '@/lib/react-query';
import { toast } from 'sonner';
import { format } from 'date-fns';



export default function PapersPage() {
    const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [sortBy, setSortBy] = useState('newest');

  const { data: papers, isLoading, error } = usePapers();
  const deletePaperMutation = useDeletePaper();

  // Ensure papers is always an array to prevent iteration errors
  // This handles: undefined, null, non-arrays
  const safePages = React.useMemo(() => {
    if (isLoading) return []; // Return empty array while loading
    return Array.isArray(papers) ? papers : [];
  }, [papers, isLoading]);

    // Filter and sort papers based on searchQuery and sortBy
    const filteredPapers = safePages.filter(paper => {
        if(!searchQuery) return true;
        const searchText = searchQuery.toLowerCase();
        
        // Handle JSONB summary field
        let summaryText = '';
        if (paper.summary) {
          if (typeof paper.summary === 'string') {
            summaryText = paper.summary;
          } else if (typeof paper.summary === 'object') {
            summaryText = JSON.stringify(paper.summary);
          }
        }
        
        return (
            paper.title?.toLowerCase().includes(searchText) ||
            paper.filename?.toLowerCase().includes(searchText) ||
            summaryText.toLowerCase().includes(searchText)
        );
    })
    .sort((a, b) => {
        switch(sortBy) {
            case 'newest':
                return new Date(b.created_at) - new Date(a.created_at);
            case 'oldest':
                return new Date(a.created_at) - new Date(b.created_at);
            case "title":
                return (a.title || a.filename || "").localeCompare(b.title || b.filename || "");
            default:
                return 0;
        }
    });

    const handlePaperClick = (paper) => {
        router.push(`/papers/${paper.id}`);
    };

    const handleDeletePaper = async (paperId, paperTitle, e) => {
        e.stopPropagation(); // Prevent triggering paper click
        try {
            await deletePaperMutation.mutateAsync(paperId);
        } catch (error) {
            console.error("Delete failed:", error);
        }
    };

  // Early loading state with skeleton
  if (isLoading) {
    return (
      <PageLayout title="Papers">
        <div className="space-y-6">
          {/* Controls skeleton */}
          <div className="flex flex-col lg:flex-row gap-4">
            <Skeleton className="h-10 flex-1" />
            <div className="flex gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-10" />
              <Skeleton className="h-10 w-10" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>
          
          {/* Paper cards skeleton */}
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Skeleton className="h-8 w-8" />
                  <div className="flex-1">
                    <Skeleton className="h-5 w-3/4 mb-2" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
                <div className="flex justify-between items-center mt-4">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      </PageLayout>
    );
  }

  // Early error state
  if (error) {
    return (
      <PageLayout title="Papers">
        <div className="text-center py-12">
          <p className="text-red-600">Failed to load papers: {error.message}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </PageLayout>
    );
  }  return (
    <PageLayout
      title="Research Papers"
      description="Browse and manage your collection of uploaded papers."
    >
      {/* Controls */}
      <div className="flex flex-col lg:flex-row gap-4 mb-8">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search papers by title, content, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        
        {/* Filters and View Controls */}
        <div className="flex gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-input rounded-md text-sm"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="title">Title A-Z</option>
          </select>
          
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="h-4 w-4" />
          </Button>
          
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
        
        <Button onClick={() => router.push('/upload')}>
          <Upload className="h-4 w-4 mr-2" />
          Upload Paper
        </Button>
      </div>

      {/* Papers Display */}
        {filteredPapers.length === 0 ? (
        <div className="text-center py-12">
          {safePages.length === 0 ? (
            <div>
              <FileText className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                No papers uploaded yet
              </h3>
              <p className="text-gray-600 mb-6">
                Start by uploading your first research paper to begin exploring AI-powered insights.
              </p>
              <Button onClick={() => router.push('/upload')}>
                <Upload className="h-4 w-4 mr-2" />
                Upload Your First Paper
              </Button>
            </div>
          ) : (
            <div>
              <Search className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                No papers found
              </h3>
              <p className="text-gray-600">
                No papers match your search criteria. Try adjusting your search terms.
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className={`
          grid gap-6
          ${viewMode === 'grid' 
            ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' 
            : 'grid-cols-1'
          }
        `}>
          <AnimatePresence>
            {filteredPapers.map((paper, index) => (
              <motion.div
                key={paper.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                layout
              >
                <Card 
                  className="hover:shadow-lg transition-all duration-200 cursor-pointer group"
                  onClick={() => handlePaperClick(paper)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <FileText className="h-8 w-8 text-blue-500 shrink-0" />
                        <div className="min-w-0 flex-1">
                          <CardTitle className="text-lg line-clamp-2">
                            {paper.title || paper.filename || 'Untitled Paper'}
                          </CardTitle>
                          <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                            {paper.filename && (
                              <span className="truncate max-w-[200px]" title={paper.filename}>
                                📄 {paper.filename}
                              </span>
                            )}
                            {paper.file_size && (
                              <span>
                                💾 {(paper.file_size / (1024 * 1024)).toFixed(2)} MB
                              </span>
                            )}
                            <span>
                              📅 {format(new Date(paper.created_at), 'MMM d, yyyy')}
                            </span>
                          </div>
                          <div className="mt-2">
                            <ProcessingBadge paper={paper} />
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePaperClick(paper);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => e.stopPropagation()}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Paper</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete &quot;{paper.title || 'Untitled Paper'}&quot;? This action cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={(e) => handleDeletePaper(paper.id, paper.title, e)}
                                className="bg-red-600 hover:bg-red-700"
                              >
                                Delete Paper
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent>
                    {/* Show AI Processing Button if needed */}
                    {(paper.processing_status === 'uploaded' || paper.processing_status === 'failed') && (
                      <div className="mb-4">
                        <ProcessingStatus 
                          paper={paper} 
                          showButton={true}
                          size="sm"
                        />
                      </div>
                    )}

                    {/* Show summary if available */}
                    {paper.summary && paper.processing_status === 'completed' && typeof paper.summary === 'object' && (
                      paper.summary.abstract || 
                      paper.summary.key_points || 
                      Object.values(paper.summary)[0]
                    ) && (
                      <div className="text-sm text-gray-600 mb-4 line-clamp-3">
                        <FormattedSummary summary={paper.summary} />
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {paper.created_at && new Date(paper.created_at).toLocaleDateString()}
                      </div>
                      
                      {paper.file_size && (
                        <div>
                          {(paper.file_size / 1024 / 1024).toFixed(1)} MB
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Results count */}
      {filteredPapers.length > 0 && (
        <div className="mt-8 text-center text-sm text-gray-500">
          Showing {filteredPapers.length} of {safePages.length} papers
          {searchQuery && ` matching "${searchQuery}"`}
        </div>
      )}
    </PageLayout>
  );
}