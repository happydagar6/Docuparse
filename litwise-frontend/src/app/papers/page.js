/**
 * Papers List Page
 * 
 * Browse and manage uploaded research papers.
 */

'use client';

import { useState } from 'react';
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
import { PageLayout } from '@/components/layout/Layout';
import { usePapers, useDeletePaper } from '@/lib/react-query';



export default function PapersPage() {
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState("grid"); // "grid" or "list"
    const [sortBy, setSortBy] = useDeletePaper();

    const { data: papers = [], isLoading, error } = usePapers();
    const deletePaperMutation = useDeletePaper();

    // Filter and sort papers based on searchQuery and sortBy
    const filteredPapers = papers.filter(paper => {
        if(!searchQuery) return true;
        const searchText = searchQuery.toLowerCase();
        return (
            paper.title?.toLowerCase().includes(searchText) ||
            paper.filename?.toLowerCase().includes(searchText) ||
            paper.summary?.toLowerCase().includes(searchText)
        );
    })
    .sort((a, b) => {
        switch(sortBy) {
            case 'newsest':
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

    const handleDeletePaper = async (paperId, e) => {
        e.stopPropagation(); // Prevent triggering paper click
        if(window.confirm("Are you you sure you want to delete this paper?")) {
            try {
                await deletePaperMutation.mutateAsync(paperId);
            } catch (error) {
                console.error("Delete failed:", error);
            }
        }
    };

if (isLoading) {
    return (
      <PageLayout title="Papers">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p>Loading papers...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout title="Papers">
        <div className="text-center py-12">
          <p className="text-red-600">Failed to load papers: {error.message}</p>
        </div>
      </PageLayout>
    );
  }

  return (
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
          {papers.length === 0 ? (
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
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => handleDeletePaper(paper.id, e)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent>
                    {paper.summary && (
                      <p className="text-sm text-gray-600 mb-4 line-clamp-3">
                        {paper.summary}
                      </p>
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
          Showing {filteredPapers.length} of {papers.length} papers
          {searchQuery && ` matching "${searchQuery}"`}
        </div>
      )}
    </PageLayout>
  );
}