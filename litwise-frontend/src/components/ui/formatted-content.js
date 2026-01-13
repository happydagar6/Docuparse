/**
 * Formatted Content Component
 * 
 * Renders AI-generated content with proper formatting for:
 * - Headers (# ## ###)
 * - Bold text (**text** or *text*)
 * - Lists (- item or * item)
 * - Line breaks and paragraphs
 */

import { memo, useMemo } from 'react';
import { cn } from '@/lib/utils';

export const FormattedContent = memo(function FormattedContent({ content, className = '' }) {
  // Memoize the expensive parsing operation
  const formattedElements = useMemo(() => {
    if (!content || typeof content !== 'string') {
      return null;
    }
    return formatText(content);
  }, [content]);

  if (!formattedElements) {
    return <div className={cn('text-slate-500 text-sm', className)}>No content available</div>;
  }

  return (
    <div className={cn('formatted-content prose prose-sm md:prose max-w-none text-slate-700', className)}>
      {formattedElements}
    </div>
  );
});

/**
 * Format text with basic markdown-like parsing
 * Moved outside component to avoid recreation on each render
 */
function formatText(text) {
  // Pre-process text to ensure proper line breaks for headers and lists
  let processedText = text
    // Add line breaks before headers if they don't exist
    .replace(/([.!?])\s*(#+\s)/g, '$1\n\n$2')
    // Add line breaks before list items if they don't exist
    .replace(/([.!?])\s*(-\s)/g, '$1\n\n$2')
    // Add line breaks after headers if they don't exist
    .replace(/(#+\s[^\n]+)([A-Z])/g, '$1\n\n$2')
    // Ensure double line breaks for proper paragraph separation
    .replace(/\n\n+/g, '\n\n')
      // Clean up any trailing spaces
      .trim();

    // Split into lines for processing
    const lines = processedText.split('\n');
    const formattedElements = [];

    let currentParagraph = [];
    let inList = false;

    lines.forEach((line, index) => {
      const trimmedLine = line.trim();

      if (!trimmedLine) {
        // Empty line - end current paragraph or list
        if (currentParagraph.length > 0) {
          formattedElements.push(
            <p key={`p-${index}`} className="mb-3 md:mb-4 leading-relaxed text-slate-700">
              {formatInlineContent(currentParagraph.join(' '))}
            </p>
          );
          currentParagraph = [];
        }
        inList = false;
        return;
      }

      // Headers
      if (trimmedLine.startsWith('### ')) {
        if (currentParagraph.length > 0) {
          formattedElements.push(
            <p key={`p-before-h3-${index}`} className="mb-3 md:mb-4 leading-relaxed text-slate-700">
              {formatInlineContent(currentParagraph.join(' '))}
            </p>
          );
          currentParagraph = [];
        }
        formattedElements.push(
          <h3 key={`h3-${index}`} className="text-base md:text-lg font-semibold mb-2.5 md:mb-3 mt-4 md:mt-5 text-slate-800 scroll-mt-20">
            {trimmedLine.replace('### ', '')}
          </h3>
        );
        inList = false;
        return;
      }

      if (trimmedLine.startsWith('## ')) {
        if (currentParagraph.length > 0) {
          formattedElements.push(
            <p key={`p-before-h2-${index}`} className="mb-3 md:mb-4 leading-relaxed text-slate-700">
              {formatInlineContent(currentParagraph.join(' '))}
            </p>
          );
          currentParagraph = [];
        }
        formattedElements.push(
          <h2 key={`h2-${index}`} className="text-lg md:text-xl font-bold mb-3 md:mb-4 mt-5 md:mt-6 text-slate-900 scroll-mt-20">
            {trimmedLine.replace('## ', '')}
          </h2>
        );
        inList = false;
        return;
      }

      if (trimmedLine.startsWith('# ')) {
        if (currentParagraph.length > 0) {
          formattedElements.push(
            <p key={`p-before-h1-${index}`} className="mb-3 md:mb-4 leading-relaxed text-slate-700">
              {formatInlineContent(currentParagraph.join(' '))}
            </p>
          );
          currentParagraph = [];
        }
        formattedElements.push(
          <h1 key={`h1-${index}`} className="text-xl md:text-2xl font-bold mb-4 md:mb-5 mt-6 md:mt-8 text-slate-900 scroll-mt-20">
            {trimmedLine.replace('# ', '')}
          </h1>
        );
        inList = false;
        return;
      }

      // List items
      if (trimmedLine.startsWith('- ') || trimmedLine.startsWith('* ') || trimmedLine.startsWith('• ')) {
        if (currentParagraph.length > 0) {
          formattedElements.push(
            <p key={`p-before-list-${index}`} className="mb-3 md:mb-4 leading-relaxed text-slate-700">
              {formatInlineContent(currentParagraph.join(' '))}
            </p>
          );
          currentParagraph = [];
        }

        if (!inList) {
          // Start new list
          inList = true;
        }

        const listContent = trimmedLine.replace(/^[-*•]\s*/, '');
        formattedElements.push(
          <div key={`li-${index}`} className="flex items-start mb-2.5 md:mb-3 gap-2.5 md:gap-3 group">
            <span className="text-blue-600 font-semibold mt-0.5 shrink-0 group-hover:text-blue-700 transition-colors">•</span>
            <span className="flex-1 text-slate-700">{formatInlineContent(listContent)}</span>
          </div>
        );
        return;
      }

      // Regular text - add to current paragraph
      inList = false;
      currentParagraph.push(line);
    });

    // Handle remaining paragraph
    if (currentParagraph.length > 0) {
      formattedElements.push(
        <p key="final-p" className="mb-3 md:mb-4 leading-relaxed text-slate-700">
          {formatInlineContent(currentParagraph.join(' '))}
        </p>
      );
    }

    return formattedElements;
}

/**
 * Format inline content (bold, italic, etc.)
 * Defined outside component to avoid recreation on each render
 */
function formatInlineContent(text) {
  if (!text) return '';

  // Split by bold patterns
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);

  return parts.map((part, index) => {
    // Bold text **text**
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic text *text*
    if (part.startsWith('*') && part.endsWith('*') && !part.includes('**')) {
      return (
        <em key={index} className="italic text-slate-800">
          {part.slice(1, -1)}
        </em>
      );
    }

    // Regular text
    return <span key={index}>{part}</span>;
  });
}

/**
 * Summary Formatter Component
 * 
 * Specifically for JSONB summary content from the database
 */
export function FormattedSummary({ summary, className = '' }) {
  if (!summary) {
    return <div className={cn('text-slate-500 text-sm', className)}>Summary not available</div>;
  }

  // Handle string summary
  if (typeof summary === 'string') {
    return <FormattedContent content={summary} className={className} />;
  }

  // Handle JSONB object summary
  if (typeof summary === 'object') {
    const sections = [];

    if (summary.abstract) {
      sections.push({
        title: 'Abstract',
        content: summary.abstract
      });
    }

    if (summary.key_points) {
      let content = summary.key_points;
      if (Array.isArray(content)) {
        content = content.map(point => `• ${point}`).join('\n');
      }
      sections.push({
        title: 'Key Points',
        content
      });
    }

    if (summary.conclusions) {
      sections.push({
        title: 'Conclusions',
        content: summary.conclusions
      });
    }

    if (summary.related_works) {
      let content = summary.related_works;
      if (Array.isArray(content)) {
        content = content.map(work => `• ${work}`).join('\n');
      }
      sections.push({
        title: 'Related Works',
        content
      });
    }

    // If no specific sections, show all available data
    if (sections.length === 0) {
      const allContent = Object.entries(summary)
        .map(([key, value]) => {
          const title = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          let content = value;
          if (Array.isArray(content)) {
            content = content.map(item => `• ${item}`).join('\n');
          }
          return `## ${title}\n${content}`;
        })
        .join('\n\n');

      return <FormattedContent content={allContent} className={className} />;
    }

    return (
      <div className={cn('space-y-4 md:space-y-5', className)}>
        {sections.map((section, index) => (
          <div key={index} className="rounded-lg border border-slate-200 p-3 md:p-4 bg-slate-50/50">
            <h4 className="font-semibold text-slate-900 mb-2 md:mb-2.5 text-sm md:text-base">{section.title}</h4>
            <div className="text-xs md:text-sm text-slate-700">
              <FormattedContent content={section.content} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <div className={cn('text-slate-500 text-sm', className)}>Invalid summary format</div>;
}