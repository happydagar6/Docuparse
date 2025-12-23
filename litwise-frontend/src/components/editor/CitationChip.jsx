/**
 * Citation Chip Component
 * Renders inline citation in the editor (e.g., "(Smith et al., 2021)")
 */


import { NodeViewWrapper } from "@tiptap/react";
import { formatAuthorsForDisplay } from "@/lib/editor-utils";
import { Button } from "../ui/button";

export default function CitationChip({ node, deleteNode }) {
    const { id, label, authors, year } = node.attrs;

    const displayText = `${formatAuthorsForDisplay(authors)}, ${year || "n.d."}`;

    return (
        <NodeViewWrapper
            as="span"
            className="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md text-sm font-medium border border-blue-200 dark:border-blue-700 cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
            contentEditable={false}>
                <span>({displayText})</span>
                <Button onClick={deleteNode}
                className="ml-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 focus:outline-none"
                aria-label="Remove citation">
                    X
                </Button>
        </NodeViewWrapper>
    )
}