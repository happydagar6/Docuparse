/**
 * Paper Reader Component
 * 
 * Displays processed research papers with AI-generated insights and interactive features.
 * 
 * COMPONENT LOGIC FLOW:
 * 1. Receives paper data (text, summary, links) from upload or search
 * 2. Displays paper content with highlighted sections
 * 3. Shows AI-generated summary and related works in sidebar
 * 4. Provides interactive navigation and highlighting
 * 5. Smooth animations for section transitions
 * 
 * FEATURES:
 * - Split-pane layout (content + sidebar)
 * - Section-based navigation
 * - Interactive highlighting
 * - AI insights display
 * - Related works suggestions
 * - Responsive design with mobile support
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Sidebar, 
  ArrowLeft, 
  BookOpen, 
  Brain, 
  Link2, 
  Download,
  Share2,
  Settings,
  ZoomIn,
  ZoomOut
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormattedContent, FormattedSummary } from '@/components/ui/formatted-content';
import { usePaperStore } from '@/lib/stores';

export function PaperReader({ paper, onBack }) {
  // Local state
  const [selectedText, setSelectedText] = useState('');
  const [contentHeight, setContentHeight] = useState('auto');
  
  // Refs
  const contentRef = useRef(null);
  const sidebarRef = useRef(null);
  
  // Zustand store for paper reader state
  const {
    showSidebar,
    highlightedSections,
    activeSection,
    fontSize,
    theme,
    toggleSidebar,
    highlightSection,
    setActiveSection,
    setFontSize,
    clearHighlights
  } = usePaperStore();

  /**
   * Handle text selection for highlighting
   */
  const handleTextSelection = () => {
    const selection = window.getSelection();
    const text = selection.toString().trim();
    
    if (text) {
      setSelectedText(text);
      // Could add annotation functionality here
    }
  };

  /**
   * Navigate to specific section
   */
  const navigateToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
      });
      setActiveSection(sectionId);
    }
  };

  /**
   * Font size controls
   */
  const increaseFontSize = () => {
    const sizes = { small: 'medium', medium: 'large', large: 'large' };
    setFontSize(sizes[fontSize]);
  };

  const decreaseFontSize = () => {
    const sizes = { small: 'small', medium: 'small', large: 'medium' };
    setFontSize(sizes[fontSize]);
  };

  /**
   * Get font size classes
   */
  const getFontSizeClass = () => {
    switch (fontSize) {
      case 'small': return 'text-sm';
      case 'large': return 'text-lg';
      default: return 'text-base';
    }
  };

  /**
   * Parse paper content into sections
   */
  const parsePaperSections = (content) => {
    if (!content) return [];
    
    // Simple section parsing - could be enhanced with more sophisticated logic
    const sections = content.split(/\n\n+/).filter(section => section.trim());
    
    return sections.map((section, index) => ({
      id: `section-${index}`,
      title: section.substring(0, 50) + (section.length > 50 ? '...' : ''),
      content: section,
      type: index === 0 ? 'abstract' : 'content'
    }));
  };

  const paperSections = parsePaperSections(
    paper?.content || paper?.content_text || paper?.extracted_text
  );

  /**
   * Helper function to extract readable text from JSONB summary
   */
  const extractSummaryText = (summary) => {
    if (!summary) return 'Summary not available';
    if (typeof summary === 'string') return summary;
    
    // Handle JSONB structure from your database
    if (typeof summary === 'object') {
      if (summary.abstract) return summary.abstract;
      if (summary.key_points && Array.isArray(summary.key_points)) {
        return summary.key_points.join('\n• ');
      }
      if (summary.conclusions) return summary.conclusions;
      // Return first available field
      const firstValue = Object.values(summary)[0];
      if (Array.isArray(firstValue)) return firstValue.join('\n• ');
      return firstValue || 'Summary processing in progress...';
    }
    
    return 'Summary not available';
  };

  /**
   * Sidebar content sections
   */
  const sidebarSections = [
    {
      id: 'summary',
      title: 'AI Summary',
      icon: Brain,
      content: extractSummaryText(paper?.summary)
    },
    {
      id: 'key_points',
      title: 'Key Points',
      icon: BookOpen,
      content: paper?.summary?.key_points 
        ? (Array.isArray(paper.summary.key_points) 
           ? paper.summary.key_points.map(point => `• ${point}`).join('\n')
           : paper.summary.key_points)
        : 'Key points will be generated based on the paper content.'
    },
    {
      id: 'related',
      title: 'Related Works',
      icon: Link2,
      content: paper?.summary?.related_works 
        ? (Array.isArray(paper.summary.related_works) 
           ? paper.summary.related_works.map(work => `• ${work}`).join('\n')
           : paper.summary.related_works)
        : 'Related works analysis in progress...'
    }
  ];

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-white/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="px-6 py-4 flex items-center justify-between">
          {/* Left side - Navigation */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <h1 className="font-semibold text-lg truncate max-w-md">
                {paper?.title || paper?.filename || 'Research Paper'}
              </h1>
            </div>
          </div>
          
          {/* Right side - Controls */}
          <div className="flex items-center gap-2">
            {/* Font size controls */}
            <Button
              variant="ghost"
              size="sm"
              onClick={decreaseFontSize}
              disabled={fontSize === 'small'}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={increaseFontSize}
              disabled={fontSize === 'large'}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            
            {/* Actions */}
            <Button variant="ghost" size="sm">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Share2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
            
            {/* Sidebar toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebar}
              className={showSidebar ? 'bg-primary/10' : ''}
            >
              <Sidebar className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Paper Content */}
        <div 
          className={`flex-1 overflow-auto transition-all duration-300 ${
            showSidebar ? 'mr-96' : 'mr-0'
          }`}
        >
          <div 
            ref={contentRef}
            className="max-w-4xl mx-auto p-8"
            onMouseUp={handleTextSelection}
          >
            {/* Paper metadata */}
            {paper?.metadata && (
              <div className="mb-8 p-6 bg-gray-50 rounded-lg">
                <h2 className="text-xl font-bold mb-2">
                  {paper.metadata.title || paper.title}
                </h2>
                {paper.metadata.authors && (
                  <p className="text-gray-600 mb-2">
                    Authors: {paper.metadata.authors}
                  </p>
                )}
                {paper.metadata.created_at && (
                  <p className="text-sm text-gray-500">
                    Uploaded: {new Date(paper.metadata.created_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
            
            {/* Paper sections */}
            <div className={`prose max-w-none ${getFontSizeClass()}`}>
              {paperSections.map((section, index) => (
                <motion.div
                  key={section.id}
                  id={section.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`mb-8 p-4 rounded-lg transition-all duration-200 ${
                    activeSection === section.id ? 'bg-primary/5 border-l-4 border-primary' : ''
                  } ${
                    highlightedSections.has(section.id) ? 'bg-yellow-50 border border-yellow-200' : ''
                  }`}
                  onClick={() => setActiveSection(section.id)}
                >
                  {section.type === 'abstract' && (
                    <h3 className="text-lg font-semibold mb-3 text-primary">
                      Abstract
                    </h3>
                  )}
                  
                  <div className="whitespace-pre-wrap leading-relaxed">
                    <FormattedContent content={section.content} />
                  </div>
                  
                  {/* Section actions */}
                  <div className="mt-4 flex gap-2 opacity-0 hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        highlightSection(section.id);
                      }}
                    >
                      Highlight
                    </Button>
                  </div>
                </motion.div>
              ))}
            </div>
            
            {/* No content fallback */}
            {paperSections.length === 0 && (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Content not available
                </h3>
                <p className="text-gray-600">
                  The paper content is still being processed or could not be extracted.
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* Sidebar */}
        <AnimatePresence>
          {showSidebar && (
            <motion.div
              ref={sidebarRef}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 20 }}
              className="fixed right-0 top-[73px] bottom-0 w-96 bg-white border-l shadow-lg z-20 overflow-auto"
            >
              <div className="p-6 space-y-6">
                {/* Sidebar sections */}
                {sidebarSections.map((section, index) => {
                  const IconComponent = section.icon;
                  
                  return (
                    <motion.div
                      key={section.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="flex items-center gap-2 text-base">
                            <IconComponent className="h-4 w-4" />
                            {section.title}
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm text-gray-700 leading-relaxed">
                          {section.id === 'summary' ? (
                            <FormattedSummary summary={paper?.summary} />
                          ) : (
                            <FormattedContent content={section.content} />
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  );
                })}
                
                {/* Section navigation */}
                {paperSections.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <BookOpen className="h-4 w-4" />
                        Sections
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {paperSections.map((section, index) => (
                          <button
                            key={section.id}
                            onClick={() => navigateToSection(section.id)}
                            className={`w-full text-left p-2 rounded text-sm transition-colors ${
                              activeSection === section.id
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-gray-100'
                            }`}
                          >
                            {section.title}
                          </button>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
                
                {/* Actions */}
                <div className="space-y-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={clearHighlights}
                    className="w-full"
                  >
                    Clear Highlights
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}