/**
 * Synthesis Panel Component
 * ========================
 *
 * Displays AI-generated research synthesis from multiple papers.
 * Shows themes, key findings, research gaps, and temporal trends.
 *
 * Props:
 * - synthesis: Object containing synthesis data from backend
 * - isLoading: Boolean indicating if synthesis is being generated
 * - error: Error object if synthesis fails
 *
 * Features:
 * - Animated loading states
 * - Collapsible sections for themes, findings, gaps
 * - Timeline visualization for publication trends
 * - Top papers list with relevance scores
 * - Gradient design with icons
 *
 * Architecture:
 * - Receives synthesis data from parent (SearchForm)
 * - Uses shadcn/ui components (Card, Badge, Button)
 * - Framer Motion for smooth animations
 * - Lucide icons for visual hierarchy
 */

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Lightbulb,
  TrendingUp,
  Search,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Target,
  Calendar,
  Award,
  AlertCircle,
  Download,
  FileText,
  FileJson,
  FileCode,
  Save,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import {
  exportSynthesisToPDF,
  exportSynthesisToJSON,
  exportSynthesisToMarkdown,
} from "@/lib/export-synthesis";
import { saveSynthesis } from "@/lib/api";

/**
 * Loading skeleton for synthesis panel
 */
function SynthesisSkeleton() {
  return (
    <Card className="mb-6 bg-linear-to-br from-purple-50 via-blue-50 to-indigo-50 border-purple-200">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-600 animate-pulse" />
          <Skeleton className="h-6 w-48" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </CardContent>
    </Card>
  );
}

/**
 * Theme Badge Component - displays a single theme with count
 */
function ThemeBadge({ theme, onClick }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="inline-block"
    >
      <Badge
        variant="secondary"
        className="cursor-pointer bg-purple-100 hover:bg-purple-200 text-purple-800 px-2 sm:px-3 py-1 text-xs sm:text-sm"
        onClick={() => onClick && onClick(theme)}
      >
        <Sparkles className="h-3 w-3 mr-1" />
        {theme.name}
        <span className="ml-1 sm:ml-2 bg-purple-200 px-1.5 sm:px-2 py-0.5 rounded-full text-xs">
          {theme.count}
        </span>
      </Badge>
    </motion.div>
  );
}

/**
 * Timeline Visualization - shows publication trends over years
 */
function TimelineChart({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return null;
  }

  // Calculate max count for scaling
  const maxCount = Math.max(...timeline.map((t) => t.count));

  return (
    <div className="space-y-2">
      {timeline.map((point, index) => {
        const barWidth = (point.count / maxCount) * 100;

        return (
          <motion.div
            key={point.year}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-2 sm:gap-3"
          >
            <span className="text-xs sm:text-sm font-medium text-gray-600 w-12 sm:w-16 shrink-0">
              {point.year}
            </span>
            <div className="flex-1 bg-gray-200 rounded-full h-5 sm:h-6 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${barWidth}%` }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="h-full bg-linear-to-r from-blue-500 to-purple-500 flex items-center justify-end pr-2"
              >
                <span className="text-xs font-semibold text-white">
                  {point.count}
                </span>
              </motion.div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

/**
 * Collapsible Section Component
 */
function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  badge,
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-purple-200/50 pt-4 first:border-t-0 first:pt-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between mb-3 hover:bg-white/50 p-2 rounded-lg transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600 shrink-0" />
          <h4 className="font-semibold text-gray-900 text-sm sm:text-base truncate">{title}</h4>
          {badge && (
            <Badge
              variant="secondary"
              className="bg-purple-100 text-purple-800 text-xs shrink-0"
            >
              {badge}
            </Badge>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-gray-500 shrink-0 ml-2" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500 shrink-0 ml-2" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="pl-4 sm:pl-7">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Main Synthesis Panel Component
 */
export function SynthesisPanel({ synthesis, isLoading, error, searchResults = [], maxPapers = 20, savedSynthesisId = null }) {
  const [isExporting, setIsExporting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(!!savedSynthesisId);
  const [currentSynthesisId, setCurrentSynthesisId] = useState(savedSynthesisId);

  // Export Handlers
  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      const result = await exportSynthesisToPDF(synthesis, synthesis.query);
      toast.success("PDF Downloaded Successfully", {
        description: `Saved as ${result.filename}`,
        duration: 3000,
      });
    } catch (error) {
      toast.error("Export failed", {
        description: error.message,
        duration: 4000,
      });
    } finally {
      setIsExporting(false);
    }
  };

  // Save synthesis to database
  const handleSaveSynthesis = async () => {
    // Prevent duplicate saves
    if (isSaved || currentSynthesisId) {
      toast.info("Already Saved", {
        description: "This synthesis has already been saved to history",
        duration: 2000,
      });
      return;
    }
    
    setIsSaving(true);
    try {
      const result = await saveSynthesis(synthesis, searchResults, maxPapers, []);
      setIsSaved(true);
      setCurrentSynthesisId(result.id);
      toast.success("Synthesis Saved Successfully", {
        description: "You can view it in the History tab",
        duration: 3000,
      });
    } catch (error) {
      toast.error("Save failed", {
        description: error.message,
        duration: 4000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportJSON = async () => {
    try {
      const result = await exportSynthesisToJSON(synthesis, synthesis.query);
      toast.success("JSON Downloaded Successfully", {
        description: `Saved as ${result.filename}`,
        duration: 3000,
      });
    } catch (error) {
      toast.error("Export failed", {
        description: error.message,
        duration: 4000,
      });
    } finally {
      setIsExporting(false);
    }
  };
  const handleExportMarkdown = () => {
    try {
      const result = exportSynthesisToMarkdown(synthesis, synthesis.query);
      toast.success("Markdown Downloaded!", {
        description: `Saved as ${result.filename}`,
        duration: 3000,
      });
    } catch (error) {
      toast.error("Export Failed", {
        description: error.message,
        duration: 5000,
      });
    }
  };
  // Show loading state
  if (isLoading) {
    return <SynthesisSkeleton />;
  }

  // Show error state
  if (error) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to generate synthesis: {error.message || "Unknown error"}
        </AlertDescription>
      </Alert>
    );
  }

  // Don't show if no synthesis data
  if (!synthesis) {
    return null;
  }

  const {
    query,
    paper_count,
    themes = [],
    key_findings = [],
    research_gaps = [],
    trends = {},
    top_papers = [],
  } = synthesis;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mb-6"
    >
      <Card className="bg-linear-to-br from-purple-50 via-blue-50 to-indigo-50 border-purple-200 shadow-lg">
        <CardHeader className="border-b border-purple-200/50 bg-white/50 p-4 sm:p-6">
          <div className="flex flex-col gap-3 sm:gap-4">
            {/* Title Row */}
            <div className="flex items-start gap-3">
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                className="bg-linear-to-br from-purple-500 to-blue-500 rounded-lg p-1.5 sm:p-2 mt-1 shrink-0"
              >
                <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </motion.div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-lg sm:text-xl text-gray-900 mb-1">
                  AI Research Synthesis
                </CardTitle>
                <p className="text-xs sm:text-sm text-gray-600">
                  Analysis of <strong>{paper_count}</strong> papers about &quot;
                  {query}&quot;
                </p>
              </div>
            </div>
            
            {/* Actions Row */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="secondary"
                className="bg-green-100 text-green-800 text-xs"
              >
                <Sparkles className="h-3 w-3 mr-1" />
                AI-Generated
              </Badge>

              {/* Save Button */}
              <Button
                variant={isSaved ? "outline" : "default"}
                size="sm"
                disabled={isSaving || isSaved}
                onClick={handleSaveSynthesis}
                className={`text-xs sm:text-sm ${isSaved ? "bg-green-50 text-green-700 border-green-300" : "bg-blue-600 hover:bg-blue-700 text-white"}`}
              >
                {isSaved ? (
                  <>
                    <Check className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    <span className="hidden xs:inline">Saved</span>
                    <span className="xs:hidden">✓</span>
                  </>
                ) : isSaving ? (
                  <>
                    <Download className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2 animate-spin" />
                    <span className="hidden sm:inline">Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    Save
                  </>
                )}
              </Button>

              {/* Export Dropdown Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isExporting}
                    className="bg-white hover:bg-gray-50 text-xs sm:text-sm"
                  >
                    <Download className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onClick={handleExportPDF}
                    className="cursor-pointer"
                  >
                    <FileText className="h-4 w-4 mr-2 text-red-500" />
                    Download as PDF
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handleExportMarkdown}
                    className="cursor-pointer"
                  >
                    <FileCode className="h-4 w-4 mr-2 text-blue-500" />
                    Download as Markdown
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handleExportJSON}
                    className="cursor-pointer"
                  >
                    <FileJson className="h-4 w-4 mr-2 text-green-500" />
                    Download as JSON
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-4 sm:pt-6 sm:p-6 space-y-4 sm:space-y-6">
          {/* Themes Section */}
          {themes.length > 0 && (
            <CollapsibleSection
              title="Main Themes"
              icon={Sparkles}
              badge={themes.length}
              defaultOpen={true}
            >
              <div className="flex flex-wrap gap-2">
                {themes.map((theme, index) => (
                  <ThemeBadge
                    key={`theme-${theme.name}-${index}`}
                    theme={theme}
                  />
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Key Findings Section */}
          {key_findings.length > 0 && (
            <CollapsibleSection
              title="Key Findings"
              icon={Lightbulb}
              badge={key_findings.length}
              defaultOpen={true}
            >
              <ul className="space-y-2">
                {key_findings.map((finding, index) => (
                  <motion.li
                    key={`finding-${finding.substring(0, 30)}-${index}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start gap-2 text-xs sm:text-sm text-gray-700 bg-white/70 p-2 sm:p-3 rounded-lg"
                  >
                    <Lightbulb className="h-3 w-3 sm:h-4 sm:w-4 text-yellow-500 mt-0.5 shrink-0" />
                    <span>{finding}</span>
                  </motion.li>
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {/* Research Gaps Section */}
          {research_gaps.length > 0 && (
            <CollapsibleSection
              title="Research Gaps"
              icon={Target}
              badge={research_gaps.length}
              defaultOpen={true}
            >
              <ul className="space-y-2">
                {research_gaps.map((gap, index) => (
                  <motion.li
                    key={`gap-${gap.substring(0, 30)}-${index}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start gap-2 text-xs sm:text-sm text-gray-700 bg-white/70 p-2 sm:p-3 rounded-lg"
                  >
                    <Target className="h-3 w-3 sm:h-4 sm:w-4 text-red-500 mt-0.5 shrink-0" />
                    <span>{gap}</span>
                  </motion.li>
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {/* Trends Section */}
          {trends.timeline && trends.timeline.length > 0 && (
            <CollapsibleSection
              title="Publication Trends"
              icon={TrendingUp}
              defaultOpen={false}
            >
              <div className="space-y-3">
                <p className="text-xs sm:text-sm text-gray-700 bg-white/70 p-2 sm:p-3 rounded-lg">
                  <Calendar className="h-3 w-3 sm:h-4 sm:w-4 inline mr-2 text-blue-500" />
                  {trends.trend_description}
                </p>
                <TimelineChart timeline={trends.timeline} />
              </div>
            </CollapsibleSection>
          )}

          {/* Top Papers Section */}
          {top_papers.length > 0 && (
            <CollapsibleSection
              title="Most Relevant Papers"
              icon={Award}
              badge={top_papers.length}
              defaultOpen={false}
            >
              <div className="space-y-2">
                {top_papers.map((paper, index) => (
                  <motion.div
                    key={`paper-${paper.id}-${index}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-white/70 p-2 sm:p-3 rounded-lg hover:bg-white/90 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm font-medium text-gray-900 line-clamp-2">
                          {paper.title}
                        </p>
                        {paper.year && (
                          <p className="text-xs text-gray-500 mt-1">
                            {paper.year}
                          </p>
                        )}
                      </div>
                      <Badge
                        variant="secondary"
                        className="bg-blue-100 text-blue-800 shrink-0 text-xs"
                      >
                        {(paper.relevance * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CollapsibleSection>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default SynthesisPanel;
