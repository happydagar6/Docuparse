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
 * TableContent Component - Displays a table with expand/collapse
 * Memoized to prevent unnecessary re-renders
 */
export const TableContent = memo(function TableContent({ table, index }) {
  const [expanded, setExpanded] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

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
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              {/* Headers */}
              {table.headers && table.headers.length > 0 && (
                <thead className="bg-muted/50 border-b">
                  <tr>
                    {table.headers.map((header, i) => (
                      <th
                        key={i}
                        className="px-3 py-2 text-left font-medium text-xs whitespace-nowrap"
                      >
                        {header || `Column ${i + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              
              {/* Body */}
              <tbody>
                {displayRows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="border-b last:border-0 hover:bg-muted/30">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-3 py-2 text-xs"
                      >
                        {cell || '-'}
                      </td>
                    ))}
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
        <DialogContent className="max-w-6xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>Table {index + 1} - Page {table.page}</DialogTitle>
          </DialogHeader>
          <div className="overflow-auto max-h-[70vh]">
            <table className="w-full text-sm border-collapse">
              {table.headers && table.headers.length > 0 && (
                <thead className="bg-muted/50 border-b sticky top-0">
                  <tr>
                    {table.headers.map((header, i) => (
                      <th
                        key={i}
                        className="px-4 py-3 text-left font-medium"
                      >
                        {header || `Column ${i + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody>
                {table.rows?.map((row, rowIndex) => (
                  <tr key={rowIndex} className="border-b hover:bg-muted/30">
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} className="px-4 py-3">
                        {cell || '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});

TableContent.displayName = 'TableContent';