/**
 * Citation Suggestion Dropdown
 * Shows available papers when user types '@'
 */

import React, { forwardRef, useImperativeHandle, useState } from 'react';
import { cn } from '@/lib/utils';
import { formatAuthorsForDisplay } from '@/lib/editor-utils';

const CitationSuggestion = forwardRef((props, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    const selectItem = (index) => {
        // Ensure index is within bounds
        const validIndex = Math.min(Math.max(0, index), props.items.length - 1);
        const item = props.items[validIndex];
        if (item) {
            props.command({ 
                id: item.id,
                label: item.title,
                authors: item.authors || [],
                year: item.year || 'n.d.'
            });
        }
    };

    const upHandler = () => {
        setSelectedIndex((prevIndex) => 
            (prevIndex + props.items.length - 1) % props.items.length
        );
    };

    const downHandler = () => {
        setSelectedIndex((prevIndex) => 
            (prevIndex + 1) % props.items.length
        );
    };

    const enterHandler = () => {
        selectItem(selectedIndex);
    };

    useImperativeHandle(ref, () => ({
        onKeyDown: ({ event }) => {
            if (event.key === 'ArrowUp') {
                upHandler();
                return true;
            }

            if (event.key === 'ArrowDown') {
                downHandler();
                return true;
            }

            if (event.key === 'Enter') {
                enterHandler();
                return true;
            }

            return false;
        },
    }));

    if (props.items.length === 0) {
        return (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm text-gray-500 dark:text-gray-400">
                No papers found
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden max-h-80 overflow-y-auto">
            {props.items.map((item, index) => {
                const authorDisplay = formatAuthorsForDisplay(item.authors || []);
                
                return (
                    <button
                        key={item.id}
                        type="button"
                        className={cn(
                            'w-full text-left px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0',
                            index === selectedIndex && 'bg-blue-50 dark:bg-blue-900/20'
                        )}
                        onClick={() => selectItem(index)}
                    >
                        <div className="font-medium text-gray-900 dark:text-gray-100 text-sm line-clamp-1">
                            {item.title}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {authorDisplay} • {item.year || 'n.d.'}
                        </div>
                    </button>
                );
            })}
        </div>
    );
});

CitationSuggestion.displayName = 'CitationSuggestion';

export default CitationSuggestion;