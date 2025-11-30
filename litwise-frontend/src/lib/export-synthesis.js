/**
 * Synthesis Export Utilities
 *
 * Provides functions to export synthesis results in multiple formats:
 * - PDF: Professional document format
 * - JSON: Machine-readable data backup
 * - Markdown: Human-readable text format
 */

import { jsPDF } from "jspdf";
import { saveAs } from "file-saver";
import { ListEnd } from "lucide-react";

/**
 * Export synthesis as PDF document
 *
 * @param {Object} synthesis - Synthesis data object
 * @param {string} query - Original search query
 */

export async function exportSynthesisToPDF(synthesis, query) {
  try {
    // Create a new PDF document (A4 size)
    const doc = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
    });

    // Page settings
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const maxWidth = pageWidth - 2 * margin;
    let yPosition = margin;

    // Helper function to add new page if needed
    const checkPageBreak = (requiredSpace = 10) => {
      if (yPosition + requiredSpace > pageHeight - margin) {
        doc.addPage();
        yPosition = margin;
        return true;
      }
      return false;
    };

    // Helper function to add wrapped text
    const addWrappedText = (text, fontSize, isBold = false) => {
      doc.setFontSize(fontSize);
      doc.setFont("helvetica", isBold ? "bold" : "normal");

      const lines = doc.splitTextToSize(text, maxWidth);
      const lineHeight = fontSize * 0.5;

      lines.forEach((line) => {
        checkPageBreak(lineHeight);
        doc.text(line, margin, yPosition);
        yPosition += lineHeight;
      });
    };

    // Title
    doc.setFontSize(20);
    doc.setFont("helvetica", "bold");
    doc.text("Research Synthesis Report", margin, yPosition);
    yPosition += 10;

    // Query - ensure it's a string
    const queryText = String(query || 'Unknown query');
    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100, 100, 100);
    doc.text(`Query: "${queryText}"`, margin, yPosition);
    yPosition += 8;

    // Metadata
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, margin, yPosition);
    yPosition += 5;
    doc.text(`Papers Analyzed: ${synthesis.paper_count || 0}`, margin, yPosition);
    yPosition += 10;

    // Horizontal line
    doc.setDrawColor(200, 200, 200);
    doc.line(margin, yPosition, pageWidth - margin, yPosition);
    yPosition += 10;

    // Reset text color
    doc.setTextColor(0, 0, 0);

    // Main themes section
    checkPageBreak(20);
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(139, 92, 246); // Purple color
    doc.text("Main Themes", margin, yPosition);
    yPosition += 8;
    doc.setTextColor(0, 0, 0);

    if (synthesis.themes && synthesis.themes.length > 0) {
      synthesis.themes.forEach((theme, index) => {
        checkPageBreak(15);

        // Theme name with number - ensure it's a string
        const themeName = String(theme.name || 'Untitled Theme');
        doc.setFontSize(12);
        doc.setFont("helvetica", "bold");
        doc.text(`${index + 1}. ${themeName}`, margin + 5, yPosition);
        yPosition += 6;

        // Theme description - ensure it's a string
        if (theme.description) {
          const themeDesc = String(theme.description);
          doc.setFontSize(10);
          doc.setFont("helvetica", "normal");
          doc.setTextColor(80, 80, 80);
          addWrappedText(themeDesc, 10);
          doc.setTextColor(0, 0, 0);
        }

        // Paper count
        doc.setFontSize(9);
        doc.setTextColor(100, 100, 100);
        doc.text(`Papers: ${theme.count || 0}`, margin + 5, yPosition);
        yPosition += 8;
        doc.setTextColor(0, 0, 0);
      });
    }
    yPosition += 5;

    // Key Findings section
    checkPageBreak(20);
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(59, 130, 246); // Blue color
    doc.text("Key Findings", margin, yPosition);
    yPosition += 8;
    doc.setTextColor(0, 0, 0);

    if (synthesis.key_findings && synthesis.key_findings.length > 0) {
        synthesis.key_findings.forEach((finding, index) => {
            checkPageBreak(12);
            doc.setFontSize(10);
            doc.setFont("helvetica", "normal");
            doc.text(`${index + 1}.`, margin + 5, yPosition);

            // Wrap finding text - ensure it's a string
            const findingText = String(finding || '');
            const findingLines = doc.splitTextToSize(findingText, maxWidth - 10);
            findingLines.forEach((line, lineIndex) => {
                if(lineIndex > 0) checkPageBreak(5);
                doc.text(line, margin + 10, yPosition);
                yPosition += 5;
            });
            yPosition += 3;
        });
    }
    yPosition += 5;

    // Research Gaps section
    checkPageBreak(20);
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(239, 68, 68); // Red color
    doc.text("Research Gaps", margin, yPosition);
    yPosition += 8;
    doc.setTextColor(0, 0, 0);

    if (synthesis.research_gaps && synthesis.research_gaps.length > 0) {
      synthesis.research_gaps.forEach((gap, index) => {
        checkPageBreak(12);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text(`${index + 1}.`, margin + 5, yPosition);
        
        // Wrap gap text - ensure it's a string
        const gapText = String(gap || '');
        const gapLines = doc.splitTextToSize(gapText, maxWidth - 10);
        gapLines.forEach((line, lineIndex) => {
          if (lineIndex > 0) checkPageBreak(5);
          doc.text(line, margin + 10, yPosition);
          yPosition += 5;
        });
        yPosition += 3;
      });
    }

    // Trends Section (if available)
    if (synthesis.trends && synthesis.trends.trend_description) {
      yPosition += 5;
      checkPageBreak(20);
      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(34, 197, 94); // Green color
      doc.text('Publication Trends', margin, yPosition);
      yPosition += 8;
      doc.setTextColor(0, 0, 0);

      // Ensure trend description is a string
      const trendDesc = String(synthesis.trends.trend_description);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      addWrappedText(trendDesc, 10);
    }

    // Footer on last page
    const totalPages = doc.internal.pages.length - 1; // jsPDF counts pages starting from 1
    for(let i = 1; i <= totalPages; i++){
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(150, 150, 150);
        doc.text(
            `Page ${i} of ${totalPages}`,
            pageWidth / 2,
            pageHeight - 10,
            { align: "center" },
        );
        doc.text(
            "Generated by Litwise AI",
            pageWidth - margin,
            pageHeight - 10,
            { align: "right" },
        );
    }

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeQuery = query.replace(/[^a-z0-9]/gi, '_').substring(0, 30);
    const filename = `synthesis_${safeQuery}_${timestamp}.pdf`;

    // Save the PDF
    doc.save(filename);

    return { success: true, message: "PDF exported successfully.", filename };

  } catch (error) {
    console.error("Error exporting synthesis to PDF:", error);
    throw new Error("Failed to export synthesis to PDF.");
  }
}


/**
 * Export synthesis as JSON file
 * 
 * @param {Object} synthesis - Synthesis data object
 * @param {string} query - Original search query
 */


export function exportSynthesisToJSON(synthesis, query) {
    try {
        // Created enhanced JSON with metadata
        const exportData = {
            metadata: {
                query,
                exported_at: new Date().toISOString(),
                paper_count: synthesis.paper_count,
                litwise_version: "1.0.0" // Example version
            },
            synthesis
        };

        // Convert to formatted JSON string
        const jsonString = JSON.stringify(exportData, null, 2);

        // Create Blob and trigger download
        const blob = new Blob([jsonString], { type: "application/json" });

        // Generate filename with timestamp
        const timestamp = new Date().toISOString().slice(0, 10);
        const safeQuery = query.replace(/[^a-z0-9]/gi, '_').substring(0, 30);
        const filename = `synthesis_${safeQuery}_${timestamp}.json`;

        saveAs(blob, filename);

        return { success: true, message: "JSON exported successfully.", filename };
    } catch (error) {
        console.error("Error exporting synthesis to JSON: " + error.message);
        throw new Error("Failed to export synthesis to JSON.");
    }
}

/**
 * Export synthesis as Markdown file
 * 
 * @param {Object} synthesis - Synthesis data object
 * @param {string} query - Original search query
 */


/**
 * Export synthesis as Markdown file
 * 
 * @param {Object} synthesis - Synthesis data object
 * @param {string} query - Original search query
 */
export function exportSynthesisToMarkdown(synthesis, query) {
  try {
    let markdown = '';

    // Header
    markdown += `# Research Synthesis Report\n\n`;
    markdown += `**Query:** "${query}"\n\n`;
    markdown += `**Generated:** ${new Date().toLocaleString()}\n\n`;
    markdown += `**Papers Analyzed:** ${synthesis.paper_count}\n\n`;
    markdown += `---\n\n`;

    // Main Themes
    markdown += `## 🎯 Main Themes\n\n`;
    if (synthesis.themes && synthesis.themes.length > 0) {
      synthesis.themes.forEach((theme, index) => {
        markdown += `### ${index + 1}. ${theme.name}\n\n`;
        if (theme.description) {
          markdown += `${theme.description}\n\n`;
        }
        markdown += `*Papers: ${theme.count}*\n\n`;
      });
    }

    // Key Findings
    markdown += `## 💡 Key Findings\n\n`;
    if (synthesis.key_findings && synthesis.key_findings.length > 0) {
      synthesis.key_findings.forEach((finding, index) => {
        markdown += `${index + 1}. ${finding}\n\n`;
      });
    }

    // Research Gaps
    markdown += `## 🔬 Research Gaps\n\n`;
    if (synthesis.research_gaps && synthesis.research_gaps.length > 0) {
      synthesis.research_gaps.forEach((gap, index) => {
        markdown += `${index + 1}. ${gap}\n\n`;
      });
    }

    // Trends
    if (synthesis.trends && synthesis.trends.trend_description) {
      markdown += `## 📈 Publication Trends\n\n`;
      markdown += `${synthesis.trends.trend_description}\n\n`;
    }

    // Footer
    markdown += `---\n\n`;
    markdown += `*Generated by Litwise AI - ${new Date().toISOString()}*\n`;

    // Create blob and trigger download
    const blob = new Blob([markdown], { type: 'text/markdown' });
    
    // Generate filename
    const timestamp = new Date().toISOString().slice(0, 10);
    const safeQuery = query.replace(/[^a-z0-9]/gi, '_').substring(0, 30);
    const filename = `synthesis_${safeQuery}_${timestamp}.md`;
    
    saveAs(blob, filename);
    
    return { success: true, filename };
  } catch (error) {
    console.error('Markdown export failed:', error);
    throw new Error('Failed to generate Markdown: ' + error.message);
  }
}
