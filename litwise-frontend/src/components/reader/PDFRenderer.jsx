'use client';

/**
 * PDF Renderer Component
 * 
 * Renders paper content as a professional PDF document using @react-pdf/renderer.
 * Features:
 * - Dynamic page generation from extracted text
 * - Proper typography and spacing
 * - Headers, body text, and lists formatting
 * - Page breaks and pagination
 * - Professional document styling
 */

import React, { memo, useMemo } from 'react';
import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  pdf,
  PDFViewer,
} from '@react-pdf/renderer';
import { Loader2 } from 'lucide-react';

// Define styles for the PDF document
const styles = StyleSheet.create({
  // Main document container
  document: {
    backgroundColor: '#ffffff',
  },

  // Page styling
  page: {
    padding: 40,
    fontSize: 11,
    lineHeight: 1.6,
    fontFamily: 'Helvetica',
  },

  // Header section
  header: {
    marginBottom: 30,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },

  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#1a1a1a',
  },

  subtitle: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 5,
  },

  // Content sections
  section: {
    marginBottom: 20,
    pageBreakInside: 'avoid',
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 15,
    marginBottom: 10,
    color: '#1a1a1a',
    pageBreakAfter: 'avoid',
  },

  subsectionTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    marginTop: 12,
    marginBottom: 8,
    color: '#333333',
    pageBreakAfter: 'avoid',
  },

  // Paragraph styling
  paragraph: {
    marginBottom: 10,
    textAlign: 'justify',
    color: '#333333',
  },

  // List styling
  list: {
    marginLeft: 20,
    marginBottom: 10,
  },

  listItem: {
    marginBottom: 5,
    marginLeft: 10,
    flexDirection: 'row',
  },

  listItemBullet: {
    width: 20,
    fontSize: 11,
  },

  listItemText: {
    flex: 1,
    color: '#333333',
  },

  // Code/preformatted text
  code: {
    fontFamily: 'Courier',
    backgroundColor: '#f5f5f5',
    padding: 8,
    marginBottom: 10,
    fontSize: 9,
    color: '#333333',
    borderLeftWidth: 3,
    borderLeftColor: '#0066cc',
  },

  // Quote styling
  blockquote: {
    marginLeft: 20,
    marginBottom: 10,
    paddingLeft: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#cccccc',
    fontStyle: 'italic',
    color: '#666666',
  },

  // Footer
  footer: {
    position: 'absolute',
    bottom: 30,
    left: 40,
    right: 40,
    textAlign: 'center',
    color: '#999999',
    fontSize: 10,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 10,
  },

  pageNumber: {
    textAlign: 'center',
    color: '#999999',
    fontSize: 10,
  },
});

/**
 * Parse markdown-like content and convert to structured sections
 */
function parseContent(text) {
  if (!text || typeof text !== 'string') return [];

  const lines = text.split('\n');
  const sections = [];
  let currentSection = null;
  let currentContent = [];

  const flushContent = () => {
    if (currentContent.length > 0) {
      if (currentSection) {
        currentSection.content = currentContent;
      }
      currentContent = [];
    }
  };

  lines.forEach((line) => {
    const trimmed = line.trim();

    // Skip empty lines if no current section
    if (!trimmed) {
      if (currentSection && currentContent.length > 0) {
        currentContent.push({ type: 'break' });
      }
      return;
    }

    // Header level 1
    if (trimmed.startsWith('# ')) {
      flushContent();
      if (currentSection) {
        sections.push(currentSection);
      }
      currentSection = {
        type: 'h1',
        text: trimmed.replace(/^# /, ''),
        content: [],
      };
      return;
    }

    // Header level 2
    if (trimmed.startsWith('## ')) {
      flushContent();
      if (currentSection) {
        sections.push(currentSection);
      }
      currentSection = {
        type: 'h2',
        text: trimmed.replace(/^## /, ''),
        content: [],
      };
      return;
    }

    // Header level 3
    if (trimmed.startsWith('### ')) {
      flushContent();
      currentContent.push({
        type: 'h3',
        text: trimmed.replace(/^### /, ''),
      });
      return;
    }

    // List items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      currentContent.push({
        type: 'listitem',
        text: trimmed.replace(/^[-*] /, ''),
      });
      return;
    }

    // Code blocks (triple backticks)
    if (trimmed.startsWith('```')) {
      if (currentSection && currentContent[currentContent.length - 1]?.type === 'code') {
        currentContent[currentContent.length - 1].isEnd = true;
      } else {
        currentContent.push({
          type: 'code',
          text: '',
          isStart: true,
        });
      }
      return;
    }

    // Blockquotes
    if (trimmed.startsWith('> ')) {
      currentContent.push({
        type: 'blockquote',
        text: trimmed.replace(/^> /, ''),
      });
      return;
    }

    // Regular paragraph
    currentContent.push({
      type: 'paragraph',
      text: trimmed,
    });
  });

  flushContent();
  if (currentSection) {
    sections.push(currentSection);
  }

  return sections;
}

/**
 * PDF Content Component - Renders the actual PDF structure
 * Memoized for performance
 */
const PDFContent = memo(function PDFContent({ title, content, metadata }) {
  const sections = useMemo(() => parseContent(content), [content]);

  return (
    <Document>
      {/* Generate pages */}
      <Page size="A4" style={styles.page}>
        {/* Header with title */}
        <View style={styles.header}>
          <Text style={styles.title}>{title}</Text>
          {metadata?.authors && (
            <Text style={styles.subtitle}>
              By {metadata.authors.join(', ')}
            </Text>
          )}
          {metadata?.year && (
            <Text style={styles.subtitle}>Published {metadata.year}</Text>
          )}
        </View>

        {/* Content sections */}
        {sections.map((section, idx) => (
          <View key={`section-${idx}`} style={styles.section}>
            {/* Section title */}
            {section.type === 'h1' && (
              <Text style={styles.sectionTitle}>{section.text}</Text>
            )}
            {section.type === 'h2' && (
              <Text style={styles.subsectionTitle}>{section.text}</Text>
            )}

            {/* Section content */}
            {section.content?.map((item, itemIdx) => {
              if (item.type === 'paragraph') {
                return (
                  <Text key={`${idx}-${itemIdx}`} style={styles.paragraph}>
                    {item.text}
                  </Text>
                );
              }

              if (item.type === 'h3') {
                return (
                  <Text key={`${idx}-${itemIdx}`} style={styles.subsectionTitle}>
                    {item.text}
                  </Text>
                );
              }

              if (item.type === 'listitem') {
                return (
                  <View
                    key={`${idx}-${itemIdx}`}
                    style={styles.listItem}
                  >
                    <Text style={styles.listItemBullet}>•</Text>
                    <Text style={styles.listItemText}>{item.text}</Text>
                  </View>
                );
              }

              if (item.type === 'blockquote') {
                return (
                  <Text key={`${idx}-${itemIdx}`} style={styles.blockquote}>
                    {item.text}
                  </Text>
                );
              }

              if (item.type === 'code') {
                return (
                  <View key={`${idx}-${itemIdx}`} style={styles.code}>
                    <Text>{item.text}</Text>
                  </View>
                );
              }

              return null;
            })}
          </View>
        ))}

        {/* Footer with page number */}
        <View style={styles.footer}>
          <Text style={styles.pageNumber}>
            Page <Text render={({ pageNumber }) => pageNumber} />
          </Text>
        </View>
      </Page>
    </Document>
  );
});

PDFContent.displayName = 'PDFContent';

/**
 * PDF Renderer Component
 * Displays PDF content dynamically with viewer
 */
export const PDFRenderer = memo(function PDFRenderer({
  title = 'Document',
  content = '',
  metadata = null,
  isLoading = false,
  error = null,
}) {
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

  return (
    <PDFViewer
      style={{
        width: '100%',
        height: '100%',
        border: 'none',
      }}
    >
      <PDFContent title={title} content={content} metadata={metadata} />
    </PDFViewer>
  );
});

PDFRenderer.displayName = 'PDFRenderer';

/**
 * Generate PDF blob from content
 * Useful for downloading or sharing the PDF
 */
export async function generatePDFBlob(title, content, metadata) {
  try {
    const doc = (
      <PDFContent title={title} content={content} metadata={metadata} />
    );
    const blob = await pdf(doc).toBlob();
    return blob;
  } catch (error) {
    console.error('Error generating PDF:', error);
    throw error;
  }
}

export default PDFRenderer;
