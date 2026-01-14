'use client';

import { memo, useState, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table as TableIcon, ChevronDown, ChevronUp, Maximize2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

/**
 * Detect if content appears to be numeric for right alignment
 */
function isNumericContent(content) {
  if (!content) return false;
  const text = String(content).trim();
  // Check if content is primarily numeric (allows commas, minus, decimals)
  return /^[-–]?[\d,\.]+%?$/.test(text);
}

/**
 * Helper function to parse and render table cell content
 * Handles HTML/markdown content with proper formatting and justification
 */
function parseCellContent(cellContent, isNumeric = false) {
  if (!cellContent) return '-';
  
  // Convert to string if needed
  let content = String(cellContent).trim();
  
  // Remove excessive whitespace and newlines, but preserve intentional spacing
  content = content.replace(/\n\s*\n/g, '\n').replace(/\s+/g, ' ').trim();
  
  // If content is empty after cleaning, return dash
  if (!content) return '-';
  
  // Detect if numeric
  const numeric = isNumeric || isNumericContent(content);
  
  // Split by <br> tags first (highest priority)
  if (content.includes('<br>') || content.includes('<br/>')) {
    const lines = content.split(/<br\s*\/?>/gi)
      .map(line => line.trim())
      .filter(line => line.length > 0);
    
    if (lines.length === 0) return '-';
    
    return (
      <div className="space-y-1">
        {lines.map((line, idx) => (
          <div 
            key={idx} 
            className={`whitespace-normal wrap-break-word ${numeric ? 'text-right font-mono' : 'text-left'} leading-relaxed`}
          >
            {renderInlineFormatting(line)}
          </div>
        ))}
      </div>
    );
  }
  
  // Regular text content with formatting
  return (
    <div className={`whitespace-normal wrap-break-word leading-relaxed ${numeric ? 'text-right font-mono' : 'text-left'}`}>
      {renderInlineFormatting(content)}
    </div>
  );
}

/**
 * Helper function to render inline formatting (bold, italic)
 * Converts markdown-style formatting to proper HTML
 */
function renderInlineFormatting(text) {
  if (!text) return '-';
  
  // First handle **bold** (must come before *italic*)
  let parts = text.split(/(\*\*[^*]+\*\*)/g);
  
  parts = parts.flatMap(part => {
    if (part.startsWith('**') && part.endsWith('**')) {
      // Bold text
      return <strong key={Math.random()} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>;
    }
    
    // Now handle *italic* in non-bold parts
    let italicParts = part.split(/(\*[^*]+\*)/g);
    return italicParts.flatMap((subPart, idx) => {
      if (subPart.startsWith('*') && subPart.endsWith('*')) {
        // Italic text
        return <em key={`${Math.random()}-${idx}`} className="italic text-slate-700">{subPart.slice(1, -1)}</em>;
      }
      
      // Handle _underline/italic_ style
      let underlineParts = subPart.split(/(_[^_]+_)/g);
      return underlineParts.flatMap((underlinePart, uIdx) => {
        if (underlinePart.startsWith('_') && underlinePart.endsWith('_')) {
          // Treat as italic/annotation
          return <em key={`${Math.random()}-${uIdx}`} className="italic text-slate-600 text-xs">{underlinePart.slice(1, -1)}</em>;
        }
        return subPart ? subPart : null;
      });
    });
  });
  
  return parts;
}

/**
 * TableContent Component - Displays a table with expand/collapse
 * Memoized to prevent unnecessary re-renders
 */
export const TableContent = memo(function TableContent({ table, index }) {
  const [expanded, setExpanded] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  // Memoize column width strategy based on content
  const getColumnClass = useCallback((colIndex, isNumeric) => {
    const baseClass = "px-3 py-2.5 text-xs md:text-sm font-semibold align-middle border-r last:border-r-0 whitespace-normal";
    
    if (isNumeric) {
      return `${baseClass} text-right w-24 min-w-fit`;
    }
    
    // First column usually larger for names/descriptions
    if (colIndex === 0) {
      return `${baseClass} text-left max-w-md`;
    }
    
    return `${baseClass} text-left max-w-sm`;
  }, []);

  const getCellClass = useCallback((colIndex, isNumeric) => {
    const baseClass = "px-3 py-2.5 text-xs md:text-sm align-top border-r last:border-r-0 break-words";
    
    if (isNumeric) {
      return `${baseClass} text-right w-24 min-w-fit font-mono`;
    }
    
    // First column usually larger for names/descriptions
    if (colIndex === 0) {
      return `${baseClass} text-left max-w-md`;
    }
    
    return `${baseClass} text-left max-w-sm`;
  }, []);

  // Memoize displayed rows to prevent recalculation
  const displayRows = useMemo(() => {
    if (!table?.rows) return [];
    return expanded ? table.rows : table.rows.slice(0, 5);
  }, [table, expanded]);

  const hasMoreRows = useMemo(() => {
    return table?.rows?.length > 5;
  }, [table]);

  const remainingRows = useMemo(() => {
    return Math.max(0, (table?.rows?.length || 0) - 5);
  }, [table]);

  // Callbacks
  const toggleExpand = useCallback(() => {
    setExpanded(prev => !prev);
  }, []);

  const openFullscreen = useCallback(() => {
    setFullscreen(true);
  }, []);

  const closeFullscreen = useCallback(() => {
    setFullscreen(false);
  }, []);

  if (!table) return null;

  return (
    <>
      <Card className="overflow-hidden transition-all hover:shadow-md">
        <div className="p-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-linear-to-br from-green-500 to-green-600 flex items-center justify-center shadow-sm">
                <TableIcon className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-medium">Table {index + 1}</p>
                <p className="text-xs text-muted-foreground">
                  Page {table.page} • {table.row_count} rows × {table.col_count} columns
                </p>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={openFullscreen}
              className="h-8 w-8 p-0"
              title="Fullscreen"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full border-collapse text-sm">
              {/* Headers */}
              {table.headers && table.headers.length > 0 && (
                <thead className="bg-linear-to-b from-slate-100 to-slate-50 border-b sticky top-0 z-10">
                  <tr>
                    {table.headers.map((header, i) => {
                      const isNumeric = isNumericContent(header);
                      return (
                        <th
                          key={i}
                          className={`${getColumnClass(i, isNumeric)} bg-slate-100 font-semibold text-slate-900 border-slate-200`}
                        >
                          {header ? parseCellContent(header, isNumeric) : `Column ${i + 1}`}
                        </th>
                      );
                    })}
                  </tr>
                </thead>
              )}
              
              {/* Body */}
              <tbody>
                {displayRows.map((row, rowIndex) => (
                  <tr key={rowIndex} className={`border-b border-slate-200 hover:bg-blue-50 transition-colors ${rowIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                    {row.map((cell, cellIndex) => {
                      const isNumeric = isNumericContent(cell);
                      return (
                        <td
                          key={cellIndex}
                          className={`${getCellClass(cellIndex, isNumeric)} border-slate-200`}
                        >
                          {parseCellContent(cell, isNumeric)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Expand/Collapse button */}
          {hasMoreRows && (
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleExpand}
              className="w-full"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-4 w-4 mr-2" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4 mr-2" />
                  Show {remainingRows} More Rows
                </>
              )}
            </Button>
          )}

          {/* Stats badge */}
          <div className="flex gap-2">
            <Badge variant="secondary" className="text-xs">
              {table.row_count} rows
            </Badge>
            <Badge variant="secondary" className="text-xs">
              {table.col_count} columns
            </Badge>
          </div>
        </div>
      </Card>

      {/* Fullscreen Dialog */}
      <Dialog open={fullscreen} onOpenChange={closeFullscreen}>
        <DialogContent className="max-w-[96vw] max-h-[96vh] w-full p-6">
          <DialogHeader className="pb-4">
            <DialogTitle className="text-lg font-semibold">
              Table {index + 1} - Page {table.page} 
              <span className="text-sm text-muted-foreground font-normal ml-2">
                ({table.row_count} rows × {table.col_count} columns)
              </span>
            </DialogTitle>
          </DialogHeader>
          <div className="overflow-auto max-h-[82vh] rounded-lg border bg-white shadow-sm">
            <table className="w-full border-collapse text-sm">
              {table.headers && table.headers.length > 0 && (
                <thead className="bg-linear-to-b from-slate-100 to-slate-50 border-b sticky top-0 z-10">
                  <tr>
                    {table.headers.map((header, i) => {
                      const isNumeric = isNumericContent(header);
                      return (
                        <th
                          key={i}
                          className={`${getColumnClass(i, isNumeric)} bg-slate-100 font-semibold text-slate-900 border-slate-200`}
                        >
                          {header ? parseCellContent(header, isNumeric) : `Column ${i + 1}`}
                        </th>
                      );
                    })}
                  </tr>
                </thead>
              )}
              <tbody>
                {table.rows?.map((row, rowIndex) => {
                  const isNumeric = isNumericContent(row[0]);
                  return (
                    <tr key={rowIndex} className={`border-b border-slate-200 hover:bg-blue-50 transition-colors ${rowIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                      {row.map((cell, cellIndex) => {
                        const cellIsNumeric = isNumericContent(cell);
                        return (
                          <td 
                            key={cellIndex} 
                            className={`${getCellClass(cellIndex, cellIsNumeric)} border-slate-200`}
                          >
                            {parseCellContent(cell, cellIsNumeric)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});

TableContent.displayName = 'TableContent';