/**
 * Search Results Panel
 * 
 * Displays search context when user navigates from search results
 * Shows the exact snippet that matched and helps user locate it in document
 */

'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Lightbulb, Copy, Search } from 'lucide-react';
import { toast } from 'sonner';

export default function SearchResultsPanel({ 
  searchContext, 
  paper, 
  onClose 
}) {
  const [isCopied, setIsCopied] = useState(false);

  if (!searchContext || !searchContext.content) return null;

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(searchContext.content || '');
    setIsCopied(true);
    toast.success('Snippet copied to clipboard');
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleFindInPage = () => {
    if (typeof window === 'undefined') return;
    
    // For PDF viewing, we use the browser's native Find feature (Ctrl+F)
    // Navigate to the correct page first if page info is available
    const pageNumber = searchContext.page || 1;
    
    // Emit event to navigate PDF viewer to the correct page
    const event = new CustomEvent('search:navigate-to-page', { 
      detail: { page: pageNumber, searchText: searchContext.content.substring(0, 100) }
    });
    window.dispatchEvent(event);
    
    // Open browser find dialog
    setTimeout(() => {
      // Use browser's find feature
      window.find(searchContext.content.substring(0, 50));
      toast.success(`Navigated to page ${pageNumber}. Use Ctrl+F to search.`);
    }, 300);
  };

  const truncatedContent = searchContext.content.length > 200
    ? `${searchContext.content.substring(0, 200)}...`
    : searchContext.content;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mb-6"
    >
      <Card className="border-l-4 border-l-blue-500 bg-linear-to-r from-blue-50 to-transparent shadow-md">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="h-5 w-5 text-blue-600" />
                <CardTitle className="text-base">You searched for this content</CardTitle>
              </div>
              {searchContext.title && (
                <p className="text-sm text-gray-600 mb-2">
                  In: <span className="font-semibold text-gray-900">{searchContext.title}</span>
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Matched Content Snippet */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
              Matched Content
            </p>
            <div className="bg-white rounded-lg border border-yellow-200 p-4 relative">
              {/* Yellow highlight indicator */}
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-yellow-400 rounded-l"></div>
              
              <p className="text-sm text-gray-800 leading-relaxed ml-2">
                <span className="bg-yellow-100 px-2 py-1 rounded">
                  {truncatedContent}
                </span>
              </p>
            </div>
          </div>

          {/* Metadata */}
          <div className="flex flex-wrap gap-2 text-xs">
            {searchContext.page && (
              <Badge variant="outline" className="bg-blue-50">
                📄 Page {searchContext.page}
              </Badge>
            )}
            {searchContext.chunk_id && (
              <Badge variant="outline" className="bg-green-50">
                📍 Section {searchContext.chunk_id.replace('node_', '')}
              </Badge>
            )}
            <Badge variant="outline" className="bg-purple-50">
              ✓ Match Found
            </Badge>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={handleFindInPage}
              className="text-xs bg-green-50 hover:bg-green-100 border-green-200"
            >
              <Search className="h-3 w-3 mr-1" />
              Highlight & Jump
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCopySnippet}
              className="text-xs"
            >
              <Copy className="h-3 w-3 mr-1" />
              {isCopied ? 'Copied!' : 'Copy'}
            </Button>
          </div>

          {/* Info Message */}
          <p className="text-xs text-gray-600 pt-2 border-t">
            💡 <strong>Tip:</strong> Click &quot;Highlight & Jump&quot; to automatically locate and highlight the text in the document, or use <kbd className="px-2 py-1 bg-gray-200 rounded text-xs font-mono">Ctrl+F</kbd> manually
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
