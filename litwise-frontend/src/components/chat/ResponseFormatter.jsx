'use client';

import React, { memo } from 'react';
import { cn } from '@/lib/utils';
import { FormattedContent } from '@/components/ui/formatted-content';

/**
 * ResponseFormatter Component
 * 
 * Structures and formats LLM responses with:
 * - Clear visual divisions
 * - Proper formatting for desktop and mobile
 * - Distinction between thinking/reasoning and final answer
 * - Responsive typography and spacing
 */
const ResponseFormatter = memo(function ResponseFormatter({
  content,
  showReasoningSection = false,
  reasoningContent = '',
  className = ''
}) {
  // Split content into sections based on common delimiters used by LLMs
  // This helps organize the response naturally
  const parsedSections = parseResponseSections(content);

  if (showReasoningSection && reasoningContent) {
    return (
      <div className={cn('space-y-4 md:space-y-5', className)}>
        {/* Reasoning Section */}
        <div className="border-l-4 border-purple-300 bg-purple-50/40 p-3 md:p-4 rounded-r-lg">
          <p className="text-xs font-semibold text-purple-700 mb-2 flex items-center gap-1.5">
            <span>💭 Thinking Process</span>
          </p>
          <div className="text-xs md:text-sm text-purple-600 leading-relaxed opacity-80">
            <FormattedContent content={reasoningContent} />
          </div>
        </div>

        {/* Main Response Section */}
        <div className="border-l-4 border-blue-300 bg-blue-50/20 p-3 md:p-4 rounded-r-lg">
          <p className="text-xs font-semibold text-blue-700 mb-2 flex items-center gap-1.5">
            <span>✨ Answer</span>
          </p>
          <div className="text-sm md:text-base text-slate-700 leading-relaxed">
            <FormattedContent content={content} />
          </div>
        </div>
      </div>
    );
  }

  // Single response without reasoning section
  return (
    <div className={cn(className)}>
      {parsedSections.length > 1 ? (
        <div className="space-y-4 md:space-y-5">
          {parsedSections.map((section, idx) => (
            <div
              key={idx}
              className={cn(
                'border-l-4 p-3 md:p-4 rounded-r-lg',
                section.type === 'conclusion' ? 'border-blue-300 bg-blue-50/20' :
                section.type === 'summary' ? 'border-green-300 bg-green-50/20' :
                section.type === 'key-point' ? 'border-amber-300 bg-amber-50/20' :
                'border-slate-300 bg-slate-50/10'
              )}
            >
              {section.label && (
                <p className="text-xs font-semibold mb-2 flex items-center gap-1.5"
                   style={{ color: getColorForType(section.type) }}>
                  <span>{section.icon}</span>
                  <span>{section.label}</span>
                </p>
              )}
              <div className="text-sm md:text-base text-slate-700 leading-relaxed">
                <FormattedContent content={section.content} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm md:text-base text-slate-700 leading-relaxed">
          <FormattedContent content={content} />
        </div>
      )}
    </div>
  );
});

/**
 * Parse response into logical sections
 * Looks for common delimiters and section markers
 */
function parseResponseSections(content) {
  if (!content || typeof content !== 'string') {
    return [];
  }

  // Common section delimiters used by LLMs
  const sectionPatterns = [
    { regex: /(?:^|\n)(In conclusion[:\s]|Conclusion[:\s]|To conclude[:\s])/mi, type: 'conclusion', icon: '🎯' },
    { regex: /(?:^|\n)(In summary[:\s]|Summary[:\s]|In short[:\s])/mi, type: 'summary', icon: '📋' },
    { regex: /(?:^|\n)(Key points[:\s]|Key takeaways[:\s]|Main points[:\s])/mi, type: 'key-point', icon: '💡' },
    { regex: /(?:^|\n)(Final thoughts[:\s]|Final answer[:\s]|Bottom line[:\s])/mi, type: 'conclusion', icon: '✨' },
  ];

  // Try to find section markers
  for (const pattern of sectionPatterns) {
    const match = content.match(pattern.regex);
    if (match) {
      const splitIndex = match.index + match[0].length;
      const beforeSection = content.substring(0, match.index).trim();
      const sectionContent = content.substring(splitIndex).trim();

      const sections = [];
      
      if (beforeSection) {
        sections.push({
          type: 'intro',
          label: null,
          icon: null,
          content: beforeSection
        });
      }

      sections.push({
        type: pattern.type,
        label: match[1].trim().replace(/[:]/g, ''),
        icon: pattern.icon,
        content: sectionContent
      });

      return sections;
    }
  }

  // No clear sections found - return as single section
  return [{ type: 'main', label: null, icon: null, content }];
}

/**
 * Get color styling based on section type
 */
function getColorForType(type) {
  const colorMap = {
    'conclusion': '#1e40af',
    'summary': '#059669',
    'key-point': '#b45309',
    'intro': '#334155',
    'main': '#334155'
  };
  return colorMap[type] || '#334155';
}

ResponseFormatter.displayName = 'ResponseFormatter';

export default ResponseFormatter;
