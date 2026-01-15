'use client';

/**
 * Advanced PDF Viewer Component
 * 
 * Features:
 * - Interactive PDF viewing with zoom controls
 * - Page navigation with keyboard shortcuts
 * - Full-screen mode
 * - Text selection and copying
 * - Print functionality
 * - Responsive design for all screen sizes
 */

import React, { useState, useCallback, useRef, memo } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Download,
  Share2,
  Printer,
  Eye,
  FileText,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

/**
 * PDF Page Renderer Component
 * Handles individual page rendering with zoom
 */
const PDFPageRenderer = memo(function PDFPageRenderer({
  pageContent,
  pageNumber,
  zoom = 1,
  onPageLoadSuccess,
  onPageLoadError,
}) {
  return (
    <div
      className="flex justify-center bg-gray-100 p-4"
      style={{
        transform: `scale(${zoom})`,
        transformOrigin: 'top center',
        transition: 'transform 0.2s ease-out',
      }}
    >
      <Card className="shadow-lg bg-white w-full max-w-3xl">
        <div className="p-8 min-h-[840px] prose prose-sm max-w-none">
          {pageContent}
        </div>
      </Card>
    </div>
  );
});

PDFPageRenderer.displayName = 'PDFPageRenderer';

/**
 * PDF Viewer Controls Component
 * Header with navigation and controls
 */
const PDFViewerControls = memo(function PDFViewerControls({
  currentPage,
  totalPages,
  zoom,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onFirstPage,
  onLastPage,
  onPreviousPage,
  onNextPage,
  onPageChange,
  onDownload,
  onPrint,
  onFullscreen,
  title,
}) {
  const [pageInput, setPageInput] = useState(currentPage.toString());

  const handlePageInputChange = (e) => {
    setPageInput(e.target.value);
  };

  const handlePageInputSubmit = (e) => {
    e.preventDefault();
    const page = parseInt(pageInput);
    if (!isNaN(page) && page >= 1 && page <= totalPages) {
      onPageChange(page);
    } else {
      setPageInput(currentPage.toString());
    }
  };

  return (
    <Card className="bg-white border-b rounded-none sticky top-0 z-20 shadow-sm">
      <div className="px-4 py-3 flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        {/* Left: Title and page info */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="shrink-0 w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
            <FileText className="h-4 w-4 text-blue-600" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {title}
            </h3>
            <p className="text-xs text-gray-500">
              PDF Viewer • {totalPages} pages
            </p>
          </div>
        </div>

        {/* Center: Navigation and zoom */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          {/* Navigation */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 border border-gray-200">
            <Button
              variant="ghost"
              size="sm"
              onClick={onFirstPage}
              disabled={currentPage === 1}
              className="h-8 w-8 p-0"
              title="First page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <form onSubmit={handlePageInputSubmit} className="flex items-center">
              <Input
                type="number"
                min="1"
                max={totalPages}
                value={pageInput}
                onChange={handlePageInputChange}
                onBlur={(e) =>
                  setPageInput(Math.max(1, Math.min(totalPages, parseInt(e.target.value) || 1)).toString())
                }
                className="w-12 h-8 text-center text-xs px-2 py-1 border-0 bg-white rounded"
              />
            </form>

            <span className="text-xs text-gray-500 px-2">/</span>
            <span className="text-xs font-semibold text-gray-700 px-2">
              {totalPages}
            </span>

            <Button
              variant="ghost"
              size="sm"
              onClick={onNextPage}
              disabled={currentPage === totalPages}
              className="h-8 w-8 p-0"
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 border border-gray-200">
            <Button
              variant="ghost"
              size="sm"
              onClick={onZoomOut}
              disabled={zoom <= 0.5}
              className="h-8 w-8 p-0"
              title="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>

            <span className="text-xs font-semibold text-gray-700 px-2 min-w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>

            <Button
              variant="ghost"
              size="sm"
              onClick={onZoomIn}
              disabled={zoom >= 2}
              className="h-8 w-8 p-0"
              title="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>

            {zoom !== 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onResetZoom}
                className="h-8 w-8 p-0 text-xs"
                title="Reset zoom"
              >
                1:1
              </Button>
            )}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={onPrint}
            className="h-8 w-8 p-0"
            title="Print"
          >
            <Printer className="h-4 w-4" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
              >
                <Eye className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Viewer Options</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onFullscreen}>
                <Maximize2 className="mr-2 h-4 w-4" />
                Full Screen
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDownload}>
                <Download className="mr-2 h-4 w-4" />
                Download PDF
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Share2 className="mr-2 h-4 w-4" />
                Share
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </Card>
  );
});

PDFViewerControls.displayName = 'PDFViewerControls';

/**
 * Advanced PDF Viewer Component
 * Main component that combines controls, viewer, and interactions
 */
export const AdvancedPDFViewer = memo(function AdvancedPDFViewer({
  title = 'Document',
  pages = [],
  isLoading = false,
  error = null,
  onDownload = null,
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  const totalPages = pages.length;

  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev + 0.2, 2));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev - 0.2, 0.5));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoom(1);
  }, []);

  const handleFirstPage = useCallback(() => {
    setCurrentPage(1);
    setZoom(1);
  }, []);

  const handleLastPage = useCallback(() => {
    setCurrentPage(totalPages);
    setZoom(1);
  }, [totalPages]);

  const handlePreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  const handleNextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  }, [totalPages]);

  const handlePageChange = useCallback((page) => {
    setCurrentPage(page);
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (e.target.tagName === 'INPUT') return;

    switch (e.key) {
      case 'ArrowLeft':
      case 'h':
        e.preventDefault();
        setCurrentPage((prev) => Math.max(1, prev - 1));
        break;
      case 'ArrowRight':
      case 'l':
        e.preventDefault();
        setCurrentPage((prev) => Math.min(totalPages, prev + 1));
        break;
      case '+':
      case '=':
        e.preventDefault();
        setZoom((prev) => Math.min(prev + 0.2, 2));
        break;
      case '-':
      case '_':
        e.preventDefault();
        setZoom((prev) => Math.max(prev - 0.2, 0.5));
        break;
      case 'f':
        e.preventDefault();
        setIsFullscreen((prev) => !prev);
        break;
      default:
        break;
    }
  }, [totalPages]);

  React.useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-gray-600 text-sm">Rendering PDF...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 font-semibold">Error rendering PDF</p>
          <p className="text-gray-600 text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  if (pages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 font-semibold">No pages available</p>
          <p className="text-gray-500 text-sm mt-1">The document appears to be empty</p>
        </div>
      </div>
    );
  }

  const currentPageContent = pages[currentPage - 1];

  return (
    <>
      <div
        ref={containerRef}
        className={cn(
          'flex flex-col h-full bg-gray-100',
          isFullscreen && 'fixed inset-0 z-50'
        )}
      >
        {/* Controls */}
        <PDFViewerControls
          currentPage={currentPage}
          totalPages={totalPages}
          zoom={zoom}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onResetZoom={handleResetZoom}
          onFirstPage={handleFirstPage}
          onLastPage={handleLastPage}
          onPreviousPage={handlePreviousPage}
          onNextPage={handleNextPage}
          onPageChange={handlePageChange}
          onDownload={onDownload}
          onPrint={() => window.print()}
          onFullscreen={() => setIsFullscreen(!isFullscreen)}
          title={title}
        />

        {/* Page display */}
        <div 
          className="flex-1 overflow-auto flex justify-center items-start pt-4 pb-4"
          data-paper-reader-content="true"
        >
          <PDFPageRenderer
            pageContent={currentPageContent}
            pageNumber={currentPage}
            zoom={zoom}
          />
        </div>

        {/* Fullscreen close button */}
        {isFullscreen && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(false)}
            className="absolute top-4 right-4 bg-white hover:bg-gray-100 z-10 h-9 w-9 p-0 rounded-lg"
          >
            <X className="h-5 w-5" />
          </Button>
        )}
      </div>
    </>
  );
});

AdvancedPDFViewer.displayName = 'AdvancedPDFViewer';

export default AdvancedPDFViewer;
