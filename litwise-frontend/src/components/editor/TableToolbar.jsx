/**
 * Table Toolbar Component
 * Provides table manipulation controls when cursor is inside a table
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
    TableRowsSplit,
    TableColumnsSplit,
    Trash2,
    MergeIcon,
    SplitIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const TableToolbarButton = ({ onClick, children, title, disabled }) => (
    <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClick}
        disabled={disabled}
        className="h-7 px-2 text-xs"
        title={title}
    >
        {children}
    </Button>
);

export default function TableToolbar({ editor }) {
    if (!editor || !editor.isActive('table')) {
        return null;
    }

    return (
        <div className="border-b border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 px-2 py-1.5 flex items-center gap-1 flex-wrap">
            <span className="text-xs font-medium text-blue-700 dark:text-blue-300 mr-2">
                Table Controls:
            </span>

            {/* Row operations */}
            <TableToolbarButton
                onClick={() => editor.chain().focus().addRowBefore().run()}
                title="Add Row Above"
            >
                ↑ Row
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().addRowAfter().run()}
                title="Add Row Below"
            >
                ↓ Row
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().deleteRow().run()}
                title="Delete Row"
                disabled={!editor.can().deleteRow()}
            >
                <Trash2 className="h-3 w-3 mr-1" />
                Row
            </TableToolbarButton>

            <Separator orientation="vertical" className="h-5 mx-1" />

            {/* Column operations */}
            <TableToolbarButton
                onClick={() => editor.chain().focus().addColumnBefore().run()}
                title="Add Column Before"
            >
                ← Col
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().addColumnAfter().run()}
                title="Add Column After"
            >
                → Col
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().deleteColumn().run()}
                title="Delete Column"
                disabled={!editor.can().deleteColumn()}
            >
                <Trash2 className="h-3 w-3 mr-1" />
                Col
            </TableToolbarButton>

            <Separator orientation="vertical" className="h-5 mx-1" />

            {/* Cell operations */}
            <TableToolbarButton
                onClick={() => editor.chain().focus().mergeCells().run()}
                title="Merge Selected Cells"
                disabled={!editor.can().mergeCells()}
            >
                Merge
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().splitCell().run()}
                title="Split Cell"
                disabled={!editor.can().splitCell()}
            >
                Split
            </TableToolbarButton>

            <Separator orientation="vertical" className="h-5 mx-1" />

            {/* Header toggle */}
            <TableToolbarButton
                onClick={() => editor.chain().focus().toggleHeaderRow().run()}
                title="Toggle Header Row"
            >
                Header Row
            </TableToolbarButton>
            <TableToolbarButton
                onClick={() => editor.chain().focus().toggleHeaderColumn().run()}
                title="Toggle Header Column"
            >
                Header Col
            </TableToolbarButton>

            <Separator orientation="vertical" className="h-5 mx-1" />

            {/* Delete table */}
            <TableToolbarButton
                onClick={() => editor.chain().focus().deleteTable().run()}
                title="Delete Entire Table"
            >
                <Trash2 className="h-3 w-3 mr-1" />
                Delete Table
            </TableToolbarButton>
        </div>
    );
}
