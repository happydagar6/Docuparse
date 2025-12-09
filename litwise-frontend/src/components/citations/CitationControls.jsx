"use client";

import {
  exportBibTeX,
  extractCitations,
  generateBatchCitations,
} from "@/lib/api";
import { useCitationStore } from "@/lib/stores";
import { useState } from "react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Filter } from "lucide-react";
import { ArrowUpDown } from "lucide-react";
import { Button } from "../ui/button";
import { Download } from "lucide-react";
import { Copy } from "lucide-react";
import { RefreshCw } from "lucide-react";

export default function CitationControls({ paperId, onRefresh }) {
  const { filterType, setFilterType, sortBy, setSortBy, selectedCitations } =
    useCitationStore();
  const [isExporting, setIsExporting] = useState(false);
  const [isReExtracting, setIsReExtracting] = useState(false);

  const handleExportBibTeX = async () => {
    if (selectedCitations.length === 0) {
      toast.error("No citations selected for export.");
      return;
    }
    setIsExporting(true);
    try {
      const bibtex = await exportBibTeX([paperId]); // Export all citations for now

      // Download as file
      const blob = new Blob([bibtex], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `citations_${paperId}.bib`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success("BibTeX exported successfully.");
    } catch (error) {
      toast.error("Failed to export BibTeX.");
      console.error("Export BibTeX error:", error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleCopyFormatted = async (format) => {
    if (selectedCitations.length === 0) {
      toast.error("No citations selected to copy.");
      return;
    }

    try {
      const response = await generateBatchCitations([paperId], format);
      const formattedText = response.citations
        .map((c) => c.citation)
        .join("\n\n");

      await navigator.clipboard.writeText(formattedText);
      toast.success(
        `Copied ${
          response.citations.length
        } citations in ${format.toUpperCase()} format.`
      );
    } catch (error) {
      toast.error("Copy failed: " + error.message);
      console.error("Copy formatted citations error:", error);
    }
  };

  const handleReExtract = async () => {
    setIsReExtracting(true);
    try {
      await extractCitations(paperId, true);
      toast.success("Citation re-extracted with AI enrichment.");
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error("Failed to re-extract citations: " + error.message);
      console.error("Re-extract citations error:", error);
    } finally {
      setIsReExtracting(false);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6 p-4 bg-gray-50 rounded-lg border">
      {/* Filter */}
      <Select value={filterType} onValueChange={setFilterType}>
        <SelectTrigger className="w-full sm:w-[180px]">
          <Filter className="w-4 h-4 mr-2" />
          <SelectValue placeholder="Filter by type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          <SelectItem value="background">Background</SelectItem>
          <SelectItem value="method">Method</SelectItem>
          <SelectItem value="comparison">Comparison</SelectItem>
          <SelectItem value="data">Data</SelectItem>
        </SelectContent>
      </Select>

      {/* Sort */}
      <Select value={sortBy} onValueChange={setSortBy}>
        <SelectTrigger className="w-full sm:w-[180px]">
          <ArrowUpDown className="w-4 h-4 mr-2" />
          <SelectValue placeholder="Sort by" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="importance">Importance</SelectItem>
          <SelectItem value="year">Year (newest)</SelectItem>
          <SelectItem value="mentions">Mentions</SelectItem>
        </SelectContent>
      </Select>

      {/* Actions */}
      <div className="flex gap-2 flex-1 justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={handleExportBibTeX}
          disabled={isExporting || selectedCitations.length === 0}
        >
          <Download className="w-4 h-4 mr-1" />
          BibTeX
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => handleCopyFormatted("apa")}
          disabled={selectedCitations.length === 0}
        >
          <Copy className="w-4 h-4 mr-1" />
          Copy APA
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={handleReExtract}
          disabled={isReExtracting}
        >
          {isReExtracting ? (
            <>
              <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
              Re-extracting...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-1" />
              AI Enrich
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
