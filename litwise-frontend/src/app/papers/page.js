/**
 * Papers List Page - Minimal Interactive Design
 * 
 * Browse and manage uploaded research papers with modern animations.
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
  Upload,
  BookOpen,
  Sparkles,
  TrendingUp
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
            // Show immediate feedback
            toast.loading('Deleting paper...', { 
                id: `delete-${paperId}`,
                description: 'Please wait while we remove your paper.'
            });
            
            await deletePaperMutation.mutateAsync(paperId);
            
            // Success is handled by the mutation hook
            toast.dismiss(`delete-${paperId}`);
            
        } catch (error) {
            console.error("Delete failed:", error);
            toast.dismiss(`delete-${paperId}`);
            // Error is handled by the mutation hook
        }
    };

  // Early loading state with skeleton
  if (isLoading) {
    return (
      <PageLayout title="Papers">
        <div className="space-y-6">
          {/* Enhanced Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-linear-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-2xl p-8 border border-blue-100 mb-8"
          >
            <div className="flex items-center gap-4 mb-4">
              <motion.div
                className="bg-linear-to-r from-blue-500 to-purple-500 rounded-xl p-3"
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <BookOpen className="h-8 w-8 text-white" />
              </motion.div>
              <div>
                <h1 className="text-3xl font-bold bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Research Papers
                </h1>
                <p className="text-gray-600 mt-1">
                  Your intelligent research library
                </p>
              </div>
            </div>
          </motion.div>
          
          {/* Controls skeleton */}
          <div className="flex flex-col lg:flex-row gap-4">
            <Skeleton className="h-12 flex-1 rounded-xl" />
            <div className="flex gap-3">
              <Skeleton className="h-12 w-36 rounded-xl" />
              <Skeleton className="h-12 w-12 rounded-xl" />
              <Skeleton className="h-12 w-12 rounded-xl" />
              <Skeleton className="h-12 w-36 rounded-xl" />
            </div>
          </div>
          
          {/* Paper cards skeleton */}
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="p-6 rounded-2xl border-2 border-gray-100 hover:border-blue-200 transition-all">
                  <div className="flex items-center gap-3 mb-4">
                    <Skeleton className="h-10 w-10 rounded-xl" />
                    <div className="flex-1">
                      <Skeleton className="h-6 w-3/4 mb-2 rounded-lg" />
                      <Skeleton className="h-4 w-20 rounded-lg" />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-full rounded-lg" />
                    <Skeleton className="h-4 w-2/3 rounded-lg" />
                  </div>
                  <div className="flex justify-between items-center mt-6">
                    <Skeleton className="h-4 w-24 rounded-lg" />
                    <Skeleton className="h-4 w-16 rounded-lg" />
                  </div>
                </Card>
              </motion.div>
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
      {/* Enhanced Interactive Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-linear-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-2xl p-8 border border-blue-100 mb-8 relative overflow-hidden"
      >
        {/* Animated Background Elements */}
        <motion.div
          className="absolute top-0 right-0 w-32 h-32 bg-linear-to-br from-blue-200/30 to-purple-200/30 rounded-full blur-xl"
          animate={{ 
            x: [0, 20, 0],
            y: [0, -10, 0],
            scale: [1, 1.1, 1]
          }}
          transition={{ duration: 6, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-24 h-24 bg-linear-to-tr from-indigo-200/30 to-blue-200/30 rounded-full blur-lg"
          animate={{ 
            x: [0, -15, 0],
            y: [0, 15, 0],
            scale: [1, 1.2, 1]
          }}
          transition={{ duration: 4, repeat: Infinity }}
        />
        
        <div className="relative z-10">
          <div className="flex items-center gap-4 mb-6">
            <motion.div
              className="bg-linear-to-r from-blue-500 to-purple-500 rounded-xl p-3"
              whileHover={{ 
                scale: 1.1, 
                rotate: 5,
                boxShadow: "0 10px 30px rgba(59, 130, 246, 0.3)"
              }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <BookOpen className="h-8 w-8 text-white" />
            </motion.div>
            <div>
              <motion.h1 
                className="text-4xl font-bold bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                Research Papers
              </motion.h1>
              <motion.p 
                className="text-gray-600 mt-2 flex items-center gap-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Sparkles className="h-4 w-4 text-purple-500" />
                Your intelligent research library
              </motion.p>
            </div>
          </div>
          
          {/* Stats Row */}
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="bg-white/60 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 rounded-lg p-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Papers</p>
                  <p className="text-xl font-semibold text-gray-900">{safePages.length}</p>
                </div>
              </div>
            </div>
            <div className="bg-white/60 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="flex items-center gap-3">
                <div className="bg-green-100 rounded-lg p-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Processed</p>
                  <p className="text-xl font-semibold text-gray-900">
                    {safePages.filter(p => p.processing_status === 'completed').length}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-white/60 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="flex items-center gap-3">
                <div className="bg-purple-100 rounded-lg p-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">AI Ready</p>
                  <p className="text-xl font-semibold text-gray-900">
                    {safePages.filter(p => p.processing_status === 'completed').length}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Enhanced Controls */}
      <motion.div 
        className="flex flex-col lg:flex-row gap-4 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        {/* Enhanced Search */}
        <div className="flex-1 relative">
          <motion.div
            className="relative"
            whileFocus={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <Input
              placeholder="Search papers by title, content, or keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 h-12 rounded-xl border-2 border-gray-200 focus:border-blue-400 transition-all bg-white/70 backdrop-blur-sm"
            />
          </motion.div>
        </div>
        
        {/* Enhanced Filters and View Controls */}
        <div className="flex gap-3">
          <motion.select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-3 border-2 border-gray-200 rounded-xl text-sm bg-white/70 backdrop-blur-sm hover:border-blue-300 transition-all min-w-[140px]"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="title">Title A-Z</option>
          </motion.select>
          
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="lg"
              onClick={() => setViewMode('grid')}
              className="h-12 w-12 rounded-xl border-2"
            >
              <Grid className="h-5 w-5" />
            </Button>
          </motion.div>
          
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="lg"
              onClick={() => setViewMode('list')}
              className="h-12 w-12 rounded-xl border-2"
            >
              <List className="h-5 w-5" />
            </Button>
          </motion.div>
        </div>
        
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button 
            onClick={() => router.push('/upload')}
            className="h-12 px-6 rounded-xl bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 border-0 shadow-lg hover:shadow-xl transition-all"
          >
            <Upload className="h-5 w-5 mr-2" />
            Upload Paper
          </Button>
        </motion.div>
      </motion.div>

      {/* Papers Display */}
        {filteredPapers.length === 0 ? (
        <motion.div 
          className="text-center py-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          {safePages.length === 0 ? (
            <div className="max-w-md mx-auto">
              <motion.div
                className="bg-linear-to-br from-blue-100 to-purple-100 rounded-full p-6 w-24 h-24 mx-auto mb-6"
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <FileText className="h-12 w-12 text-blue-600 mx-auto" />
              </motion.div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">
                No papers uploaded yet
              </h3>
              <p className="text-gray-600 mb-8 leading-relaxed">
                Start by uploading your first research paper to begin exploring AI-powered insights and unlock intelligent analysis.
              </p>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Button 
                  onClick={() => router.push('/upload')}
                  className="px-8 py-4 rounded-xl bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0 shadow-lg hover:shadow-xl transition-all"
                >
                  <Upload className="h-5 w-5 mr-2" />
                  Upload Your First Paper
                </Button>
              </motion.div>
            </div>
          ) : (
            <div className="max-w-md mx-auto">
              <motion.div
                className="bg-linear-to-br from-gray-100 to-blue-100 rounded-full p-6 w-24 h-24 mx-auto mb-6"
                whileHover={{ scale: 1.1 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <Search className="h-12 w-12 text-gray-600 mx-auto" />
              </motion.div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">
                No papers found
              </h3>
              <p className="text-gray-600">
                No papers match your search criteria. Try adjusting your search terms or filters.
              </p>
            </div>
          )}
        </motion.div>
      ) : (
        <motion.div 
          className={`
            grid gap-6
            ${viewMode === 'grid' 
              ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' 
              : 'grid-cols-1'
            }
          `}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          <AnimatePresence mode="wait">
            {filteredPapers.map((paper, index) => (
              <motion.div
                key={paper.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                layout
                whileHover={{ y: -8 }}
              >
                <Card 
                  className="relative group overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-2xl border-2 border-gray-100 hover:border-blue-200 rounded-2xl bg-white/80 backdrop-blur-sm"
                  onClick={() => handlePaperClick(paper)}
                >
                  {/* Gradient Overlay */}
                  <div className="absolute inset-0 bg-linear-to-br from-blue-50/0 via-purple-50/0 to-blue-50/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  {/* Animated Background Elements */}
                  <motion.div
                    className="absolute top-2 right-2 w-16 h-16 bg-linear-to-br from-blue-200/20 to-purple-200/20 rounded-full blur-xl opacity-0 group-hover:opacity-100"
                    animate={{ 
                      scale: [1, 1.2, 1],
                      rotate: [0, 180, 360]
                    }}
                    transition={{ duration: 8, repeat: Infinity }}
                  />
                  
                  <CardHeader className="pb-4 relative z-10">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <motion.div
                          className="bg-linear-to-br from-blue-500 to-purple-500 rounded-xl p-3 shrink-0"
                          whileHover={{ scale: 1.1, rotate: 5 }}
                          transition={{ type: "spring", stiffness: 300 }}
                        >
                          <FileText className="h-6 w-6 text-white" />
                        </motion.div>
                        <div className="min-w-0 flex-1">
                          <CardTitle className="text-xl font-bold line-clamp-2 mb-2 group-hover:text-blue-600 transition-colors">
                            {paper.title || paper.filename || 'Untitled Paper'}
                          </CardTitle>
                          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
                            {paper.filename && (
                              <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded-lg truncate max-w-[200px]" title={paper.filename}>
                                📄 {paper.filename}
                              </span>
                            )}
                            {paper.file_size && (
                              <span className="flex items-center gap-1 bg-blue-100 text-blue-700 px-2 py-1 rounded-lg">
                                💾 {(paper.file_size / (1024 * 1024)).toFixed(2)} MB
                              </span>
                            )}
                            <span className="flex items-center gap-1 bg-purple-100 text-purple-700 px-2 py-1 rounded-lg">
                              📅 {format(new Date(paper.created_at), 'MMM d, yyyy')}
                            </span>
                          </div>
                          <div className="mt-3">
                            <ProcessingBadge paper={paper} />
                          </div>
                        </div>
                      </div>
                      
                      {/* Enhanced Action Buttons - Always Visible */}
                      <div className="flex gap-1 transition-all duration-300">
                        <motion.div
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePaperClick(paper);
                            }}
                            className="h-10 w-10 rounded-xl hover:bg-blue-100 hover:text-blue-600"
                            title="View paper details"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </motion.div>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <motion.div
                              whileHover={{ scale: 1.1 }}
                              whileTap={{ scale: 0.95 }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-10 w-10 rounded-xl hover:bg-red-100 hover:text-red-600 transition-all duration-200 group/delete"
                                title="Delete paper permanently"
                              >
                                <motion.div
                                  whileHover={{ rotate: 10 }}
                                  transition={{ type: "spring", stiffness: 300 }}
                                >
                                  <Trash2 className="h-4 w-4 group-hover/delete:scale-110 transition-transform" />
                                </motion.div>
                              </Button>
                            </motion.div>
                          </AlertDialogTrigger>
                          <AlertDialogContent className="rounded-2xl border-2 max-w-md">
                            <AlertDialogHeader className="text-center pb-4">
                              <motion.div
                                className="bg-red-100 rounded-full p-4 w-16 h-16 mx-auto mb-4"
                                initial={{ scale: 0.8, rotate: -10 }}
                                animate={{ scale: 1, rotate: 0 }}
                                transition={{ type: "spring", stiffness: 300 }}
                              >
                                <Trash2 className="h-8 w-8 text-red-600 mx-auto" />
                              </motion.div>
                              <AlertDialogTitle className="text-2xl font-bold text-gray-900">
                                Delete Paper?
                              </AlertDialogTitle>
                              <AlertDialogDescription className="text-gray-600 leading-relaxed">
                                Are you sure you want to permanently delete{" "}
                                <span className="font-semibold text-gray-900">
                                  &quot;{(paper.title || paper.filename || 'Untitled Paper').length > 40 
                                    ? (paper.title || paper.filename || 'Untitled Paper').substring(0, 40) + '...'
                                    : (paper.title || paper.filename || 'Untitled Paper')}&quot;
                                </span>?
                                <br /><br />
                                <span className="text-red-600 font-medium">
                                  This action cannot be undone and all associated data, chat history, and AI analysis will be permanently removed.
                                </span>
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter className="gap-3 pt-6">
                              <AlertDialogCancel className="rounded-xl flex-1 h-12">
                                Keep Paper
                              </AlertDialogCancel>
                              <AlertDialogAction
                                onClick={(e) => handleDeletePaper(paper.id, paper.title, e)}
                                className="bg-red-500 hover:bg-red-600 rounded-xl flex-1 h-12 font-semibold"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete Forever
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent className="relative z-10">
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

                    {/* Enhanced summary display */}
                    {paper.summary && paper.processing_status === 'completed' && typeof paper.summary === 'object' && (
                      paper.summary.abstract || 
                      paper.summary.key_points || 
                      Object.values(paper.summary)[0]
                    ) && (
                      <div className="bg-linear-to-r from-blue-50 to-purple-50 rounded-xl p-4 mb-4 border border-blue-100">
                        <div className="text-sm text-gray-700 line-clamp-3">
                          <FormattedSummary summary={paper.summary} />
                        </div>
                      </div>
                    )}
                    
                    {/* Enhanced metadata */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 text-gray-500">
                        <Calendar className="h-4 w-4" />
                        <span className="font-medium">
                          {paper.created_at && new Date(paper.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      
                      {paper.file_size && (
                        <div className="bg-gray-100 px-2 py-1 rounded-lg text-gray-600 font-medium">
                          {(paper.file_size / 1024 / 1024).toFixed(1)} MB
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Enhanced Results count */}
      {filteredPapers.length > 0 && (
        <motion.div 
          className="mt-12 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
        >
          <div className="bg-linear-to-r from-blue-50 via-indigo-50 to-purple-50 rounded-2xl p-6 border border-blue-100 max-w-md mx-auto">
            <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
              <motion.div
                className="bg-blue-500 rounded-full p-1"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Sparkles className="h-3 w-3 text-white" />
              </motion.div>
              <span className="font-medium">
                Showing <span className="text-blue-600 font-bold">{filteredPapers.length}</span> of{" "}
                <span className="text-purple-600 font-bold">{safePages.length}</span> papers
                {searchQuery && (
                  <>
                    {" "}matching <span className="text-indigo-600 font-bold">&quot;{searchQuery}&quot;</span>
                  </>
                )}
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </PageLayout>
  );
}