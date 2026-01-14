'use client';

/**
 * Paper PDF Viewer Integration Component
 * 
 * Converts extracted paper content into formatted PDF pages using backend page_info.
 * Features:
 * - Uses actual page boundaries from PDF extraction
 * - Proper typography and formatting
 * - Image and table integration
 * - Responsive design
 */

import React, { useMemo, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import AdvancedPDFViewer from './AdvancedPDFViewer';
import Image from 'next/image';

/**
 * Split markdown content into pages based on content length
 * Tries to break at section boundaries when possible
 */
function splitMarkdownIntoPages(markdownContent, pageSize = 3000) {
  if (!markdownContent) return [];
  
  const pages = [];
  let currentPage = '';
  let charCount = 0;
  
  // Split by double newlines (paragraphs) to preserve structure
  const paragraphs = markdownContent.split('\n\n');
  
  paragraphs.forEach((paragraph) => {
    const paraLength = paragraph.length + 2; // +2 for newlines
    
    // If adding this paragraph exceeds limit and we have content, start new page
    if (charCount + paraLength > pageSize && currentPage.trim()) {
      pages.push(currentPage.trim());
      currentPage = paragraph;
      charCount = paraLength;
    } else {
      // Add to current page
      if (currentPage) {
        currentPage += '\n\n' + paragraph;
      } else {
        currentPage = paragraph;
      }
      charCount += paraLength;
    }
  });
  
  // Don't forget the last page
  if (currentPage.trim()) {
    pages.push(currentPage.trim());
  }
  
  return pages.length > 0 ? pages : [markdownContent];
}

/**
 * Markdown renderer component for tables and content
 */
const MarkdownRenderer = memo(function MarkdownRenderer({ content }) {
  return (
    <ReactMarkdown
      components={{
        // Wrapper
        div: ({ children }) => (
          <div className="prose prose-sm max-w-none text-gray-800">
            {children}
          </div>
        ),
        // Headers
        h1: ({ children }) => <h1 className="text-2xl font-bold mt-4 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-xl font-bold mt-3 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-lg font-bold mt-3 mb-1">{children}</h3>,
        p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
        
        // Lists
        ul: ({ children }) => <ul className="list-disc list-inside mb-3 ml-4">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-3 ml-4">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        
        // Tables
        table: ({ children }) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border-collapse border border-gray-300">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-gray-100 border-b-2 border-gray-300">
            {children}
          </thead>
        ),
        tbody: ({ children }) => (
          <tbody>{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="border-b border-gray-300">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="border border-gray-300 px-4 py-2 text-left font-semibold bg-gray-50">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-gray-300 px-4 py-2">
            {children}
          </td>
        ),
        
        // Code blocks
        code: ({ inline, children }) => 
          inline ? (
            <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">{children}</code>
          ) : (
            <pre className="bg-gray-100 p-4 rounded mb-3 overflow-x-auto">
              <code className="text-sm font-mono">{children}</code>
            </pre>
          ),
        
        // Images
        img: ({ src, alt }) => (
          <figure className="my-4">
            <Image 
              src={src} 
              alt={alt} 
              className="max-w-full h-auto rounded-lg shadow-sm"
            />
            {alt && <figcaption className="text-sm text-gray-600 mt-2 text-center">{alt}</figcaption>}
          </figure>
        ),
        
        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-600 my-3">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
});

function createPageComponents(markdownContent, metadata) {
  // Split markdown into logical pages
  const markdownPages = splitMarkdownIntoPages(markdownContent, 3000);
  
  console.log('createPageComponents DEBUG:', {
    contentLength: markdownContent?.length,
    pageCount: markdownPages.length,
    hasMarkdown: !!markdownContent,
  });

  return markdownPages.map((pageContent, idx) => (
    <div key={`page-${idx}`} className="bg-white p-8 min-h-[1122px] text-sm leading-relaxed">
      {/* Page Header with metadata on first page */}
      {idx === 0 && (
        <div className="mb-8 pb-6 border-b-2 border-gray-200">
          {metadata?.title && (
            <h1 className="text-2xl font-bold mb-2 text-gray-900">
              {metadata.title}
            </h1>
          )}
          {metadata?.authors && metadata.authors.length > 0 && (
            <p className="text-gray-600 mb-1">
              By {metadata.authors.join(', ')}
            </p>
          )}
          {metadata?.year && (
            <p className="text-gray-500 text-sm">
              Published {metadata.year}
            </p>
          )}
        </div>
      )}

      {/* Page content - Use markdown renderer for tables and images */}
      <MarkdownRenderer content={pageContent} />

      {/* Page footer */}
      <div className="mt-12 pt-6 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
        <span>{metadata?.title || 'Document'}</span>
        <span>Page {idx + 1} of {markdownPages.length}</span>
      </div>
    </div>
  ));
}

/**
 * Paper PDF Viewer Component
 * Main component that integrates with PaperReader
 */
export const PaperPDFViewer = memo(function PaperPDFViewer({
  paper,
  isLoading = false,
  error = null,
  onDownload = null,
}) {
  // Memoize page generation to prevent unnecessary re-renders
  const pages = useMemo(() => {
    // Prefer markdown_content which has tables and images, fallback to content_text
    const content = paper?.markdown_content || paper?.content || paper?.content_text || paper?.extracted_text;
    
    if (!content) {
      console.warn('PaperPDFViewer: No content available in paper object', {
        hasMarkdown: !!paper?.markdown_content,
        hasContent: !!paper?.content,
        hasContentText: !!paper?.content_text,
      });
      return [];
    }

    console.log('PaperPDFViewer: Content loaded', {
      contentLength: content?.length,
      contentType: typeof content,
      isMarkdown: !!paper?.markdown_content,
      firstChars: content?.substring(0, 100),
    });
    
    const metadata = {
      title: paper?.title || paper?.filename || 'Research Paper',
      authors: paper?.authors || [],
      year: paper?.publication_year || paper?.year || null,
    };

    const pageComponents = createPageComponents(content, metadata);
    console.log('PaperPDFViewer: Pages created', {
      pageCount: pageComponents.length,
      contentLength: content?.length,
      usedMarkdown: !!paper?.markdown_content,
    });
    
    return pageComponents;
  }, [paper]);

  // Handle download
  const handleDownload = useCallback(async () => {
    try {
      if (onDownload) {
        await onDownload();
      } else {
        // Default download implementation
        console.log('Download not implemented');
      }
    } catch (err) {
      console.error('Error downloading PDF:', err);
    }
  }, [onDownload]);

  return (
    <AdvancedPDFViewer
      title={paper?.title || paper?.filename || 'Research Paper'}
      pages={pages}
      isLoading={isLoading}
      error={error}
      onDownload={handleDownload}
    />
  );
});

PaperPDFViewer.displayName = 'PaperPDFViewer';

export default PaperPDFViewer;
