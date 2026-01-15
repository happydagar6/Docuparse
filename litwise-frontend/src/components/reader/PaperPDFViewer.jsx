'use client';

/**
 * PDF Viewer Component using react-pdf
 * 
 * Renders actual PDF pages from original document for perfect formatting.
 * Features:
 * - True PDF rendering - no extraction artifacts
 * - Tables display exactly as in original PDF
 * - All formatting and images preserved
 * - Page navigation
 * - Text search and highlighting support
 */

import React, { useState, useMemo, useCallback, memo, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { FileX, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

// Set up PDF.js worker - reference from public folder (no CORS issues)
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';
}

/**
 * PDF Page Renderer Component
 * Renders all PDF pages in a scrollable view
 */
const PDFPageRenderer = memo(function PDFPageRenderer({ 
  pdfUrl, 
  numPages,
  onLoadSuccess,
  onLoadError,
  scale = 1
}) {
  // Don't return null here - we need to render the Document to get numPages
  // The Document component will handle loading state
  
  return (
    <Document
      file={pdfUrl}
      onLoadSuccess={onLoadSuccess}
      onLoadError={onLoadError}
      loading={<div className="flex items-center justify-center h-96 bg-gray-50">Loading PDF...</div>}
      error={<div className="flex items-center justify-center h-96 bg-gray-50 text-red-500">Error loading PDF</div>}
    >
      {numPages && Array.from({ length: numPages }, (_, i) => (
        <div key={i + 1} className="flex justify-center bg-gray-100 py-2 sm:py-4 px-2 sm:px-0">
          <div className="bg-white shadow-lg" style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}>
            <Page 
              pageNumber={i + 1}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              width={Math.min(600, window.innerWidth - 40)}
            />
          </div>
        </div>
      ))}
    </Document>
  );
});

/**
 * Paper PDF Viewer Component
 * Main component that uses actual PDF file instead of extracted markdown
 */
export const PaperPDFViewer = memo(function PaperPDFViewer({
  paper,
  isLoading = false,
  error = null,
  onDownload = null,
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [numPages, setNumPages] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [scale, setScale] = useState(1);

  // Get PDF URL from paper object
  const pdfUrl = useMemo(() => {
    const url = paper?.pdf_url;
    if (!url) {
      return null;
    }
    
    // Handle if pdf_url is a JSON object with signedURL property
    if (typeof url === 'object' && url.signedURL) {
      return url.signedURL;
    }
    
    // Handle if pdf_url is a JSON string that needs parsing
    if (typeof url === 'string' && url.startsWith('{')) {
      try {
        const parsed = JSON.parse(url);
        return parsed.signedURL || parsed;
      } catch (e) {
        return url;
      }
    }
    
    return url;
  }, [paper?.pdf_url]);

  // Check if PDF is available
  const hasPdf = useMemo(() => {
    return !!pdfUrl;
  }, [pdfUrl]);

  // Handle PDF load success
  const handleLoadSuccess = useCallback(({ numPages: pages }) => {
    setNumPages(pages);
    setPdfError(null);
  }, []);

  // Handle PDF load error
  const handleLoadError = useCallback((error) => {
    console.error('PDF loading error:', error);
    setPdfError(error?.message || 'Failed to load PDF');
  }, []);

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setScale(prev => Math.min(prev + 0.2, 2));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale(prev => Math.max(prev - 0.2, 0.8));
  }, []);

  const handleResetZoom = useCallback(() => {
    setScale(1);
  }, []);

  // Navigation handlers
  const goToPreviousPage = useCallback(() => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage(prev => Math.min(numPages || prev, prev + 1));
  }, [numPages]);

  const goToPage = useCallback((pageNum) => {
    const page = Math.max(1, Math.min(numPages || pageNum, pageNum));
    setCurrentPage(page);
  }, [numPages]);

  // Listen for search navigation events
  useEffect(() => {
    const handleSearchNavigation = (event) => {
      const { page } = event.detail;
      if (page && numPages) {
        goToPage(page);
      }
    };

    window.addEventListener('search:navigate-to-page', handleSearchNavigation);
    return () => window.removeEventListener('search:navigate-to-page', handleSearchNavigation);
  }, [goToPage, numPages]);

  // Handle download
  const handleDownload = useCallback(async () => {
    try {
      if (onDownload) {
        await onDownload();
      } else if (pdfUrl) {
        // Download PDF directly from URL
        const link = document.createElement('a');
        link.href = pdfUrl;
        link.download = `${paper?.title || 'document'}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (err) {
      console.error('Error downloading PDF:', err);
    }
  }, [paper, pdfUrl, onDownload]);

  // Show loading state if paper is still loading
  if (isLoading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading paper...</p>
        </div>
      </div>
    );
  }

  // Show error state if there was an error
  if (error) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <FileX size={64} className="mx-auto mb-4 text-red-400" />
          <h3 className="text-xl font-semibold mb-2 text-gray-800">Error Loading Paper</h3>
          <p className="text-gray-600 mb-2">
            {error?.message || 'An error occurred while loading the paper'}
          </p>
          <p className="text-sm text-gray-500">
            Please try again or contact support if the problem persists.
          </p>
        </div>
      </div>
    );
  }

  // If no PDF URL available, show fallback message or markdown content
  if (!hasPdf) {
    const markdownContent = paper?.markdown_content || paper?.content_text || paper?.content;
    console.log('PaperPDFViewer - No PDF, checking for fallback content:', {
      hasMarkdownContent: !!paper?.markdown_content,
      hasContentText: !!paper?.content_text,
      hasContent: !!paper?.content,
      willShowMarkdown: !!markdownContent
    });
    
    // If we have extracted markdown content, show it as fallback
    if (markdownContent) {
      console.log('PaperPDFViewer - Showing markdown fallback');
      return (
        <div className="w-full h-screen flex flex-col bg-gray-50">
          <div className="flex-1 overflow-y-auto p-6 md:p-8">
            <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-sm p-6 md:p-8">
              <div className="prose prose-sm md:prose-base max-w-none">
                <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {markdownContent}
                </div>
              </div>
            </div>
          </div>
          <div className="px-4 py-3 bg-amber-50 border-t border-amber-200 text-amber-700">
            <p className="text-xs sm:text-sm flex items-center gap-2">
              <span className="inline-block">ℹ️</span>
              Original PDF file not available. Showing extracted content instead.
            </p>
          </div>
        </div>
      );
    }
    
    // No PDF and no extracted content
    console.log('PaperPDFViewer - No PDF and no fallback content');
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <FileX size={64} className="mx-auto mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold mb-2 text-gray-800">PDF Not Available</h3>
          <p className="text-gray-600 mb-4">
            The PDF file for this document is not available. Please re-upload the document.
          </p>
          {paper?.title && (
            <p className="text-sm text-gray-500">
              Document: {paper.title}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Main PDF viewer layout
  return (
    <div className="w-full h-screen flex flex-col bg-gray-50">
      {/* Zoom Controls - Mobile friendly */}
      <div className="flex items-center justify-center gap-2 p-3 bg-white border-b border-gray-200 shadow-sm">
        <button
          onClick={handleZoomOut}
          disabled={scale <= 0.8}
          className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Zoom out"
        >
          <ZoomOut size={20} className="text-gray-600" />
        </button>
        
        <span className="text-sm font-medium text-gray-700 min-w-12 text-center">
          {Math.round(scale * 100)}%
        </span>
        
        <button
          onClick={handleZoomIn}
          disabled={scale >= 2}
          className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Zoom in"
        >
          <ZoomIn size={20} className="text-gray-600" />
        </button>
        
        <button
          onClick={handleResetZoom}
          disabled={scale === 1}
          className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Reset zoom"
        >
          <RotateCcw size={20} className="text-gray-600" />
        </button>
      </div>

      {/* PDF Display Area - scrollable */}
      <div className="flex-1 overflow-y-auto overflow-x-auto bg-gray-100">
        <div className="flex flex-col items-center min-h-full">
          <PDFPageRenderer 
            pdfUrl={pdfUrl}
            numPages={numPages}
            onLoadSuccess={handleLoadSuccess}
            onLoadError={handleLoadError}
            scale={scale}
          />
        </div>
      </div>

      {/* Error message if PDF failed to load */}
      {pdfError && (
        <div className="flex items-center justify-center gap-3 p-4 bg-red-50 border-t border-red-200 text-red-700">
          <FileX size={20} />
          <div>
            <p className="font-semibold">PDF Loading Error</p>
            <p className="text-sm">{pdfError}</p>
          </div>
        </div>
      )}
    </div>
  );
})

PaperPDFViewer.displayName = 'PaperPDFViewer';

export default PaperPDFViewer;
