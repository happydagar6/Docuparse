"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getPapers } from "@/lib/api";
import { generateLiteratureReview } from "@/lib/literature-review-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import { Loader2, FileText, Sparkles } from "lucide-react";

const REVIEW_STYLES = [
  {
    value: "narrative",
    label: "Narrative",
    description: "Flowing story of research",
  },
  {
    value: "systematic",
    label: "Systematic",
    description: "Structured and methodical",
  },
  {
    value: "critical",
    label: "Critical",
    description: "Analytical and evaluative",
  },
];

export default function ReviewGenerator({ onReviewGenerated }) {
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [topic, setTopic] = useState("");
  const [reviewStyle, setReviewStyle] = useState("narrative");
  const [wordLimit, setWordLimit] = useState(3000);

  const { data: papersData, isLoading: papersLoading } = useQuery({
    queryKey: ["papers"],
    queryFn: getPapers,
  });

  // API returns array directly, not { papers: [...] }
  const papers = Array.isArray(papersData)
    ? papersData
    : papersData?.papers || [];

  const generateMutation = useMutation({
    mutationFn: generateLiteratureReview,
    onSuccess: (data) => {
      toast.success("Literature review generated!");
      onReviewGenerated(data);
    },
    onError: (error) => {
      toast.error(error.message || "Failed to generate review");
    },
  });

  const handlePaperToggle = (paperId) => {
    setSelectedPapers((prev) =>
      prev.includes(paperId)
        ? prev.filter((id) => id !== paperId)
        : [...prev, paperId]
    );
  };

  const handleSelectAll = () => {
    if (selectedPapers.length === papers.length) {
      setSelectedPapers([]);
    } else {
      setSelectedPapers(papers.map((p) => p.id));
    }
  };

  const handleGenerate = () => {
    if (selectedPapers.length === 0) {
      toast.error("Please select at least one paper");
      return;
    }
    if (!topic.trim()) {
      toast.error("Please enter a topic");
      return;
    }

    generateMutation.mutate({
      paper_ids: selectedPapers,
      topic: topic.trim(),
      review_style: reviewStyle,
      word_limit: wordLimit,
    });
  };

  return (
    <Card className="border-2 shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-3 bg-linear-to-br from-pink-50 to-transparent">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="p-1.5 bg-pink-100 rounded-lg">
            <Sparkles className="h-4 w-4 text-pink-600" />
          </div>
          Generate Review
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Topic Input */}
        <div className="space-y-2">
          <Label htmlFor="topic" className="font-medium">
            Review Topic
          </Label>
          <Input
            id="topic"
            placeholder="e.g., Machine Learning in Healthcare"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="border-2 focus:border-primary transition-colors"
          />
        </div>

        {/* Review Style */}
        <div className="space-y-2">
          <Label className="font-medium">Review Style</Label>
          <Select value={reviewStyle} onValueChange={setReviewStyle}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {REVIEW_STYLES.map((style) => (
                <SelectItem key={style.value} value={style.value}>
                  <div>
                    <span className="font-medium">{style.label}</span>
                    <span className="text-muted-foreground ml-2 text-xs">
                      - {style.description}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Word Limit */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <Label className="font-medium">Word Limit</Label>
            <span className="text-sm font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
              {wordLimit.toLocaleString()}
            </span>
          </div>
          <Slider
            value={[wordLimit]}
            onValueChange={([value]) => setWordLimit(value)}
            min={500}
            max={10000}
            step={500}
            className="cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>500</span>
            <span>10,000</span>
          </div>
        </div>

        {/* Paper Selection */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <Label className="font-medium">
              Select Papers
              <span className="ml-2 text-xs font-normal text-primary bg-primary/10 px-2 py-0.5 rounded">
                {selectedPapers.length}/{papers.length}
              </span>
            </Label>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSelectAll}
              disabled={papers.length === 0}
              className="hover:bg-primary/10 hover:text-primary transition-colors"
            >
              {selectedPapers.length === papers.length
                ? "Deselect All"
                : "Select All"}
            </Button>
          </div>
          <div className="max-h-[220px] overflow-y-auto space-y-1.5 border-2 rounded-lg p-2.5 bg-gray-50/50 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
            {papersLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Loading papers...
                </span>
              </div>
            ) : papers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <div className="p-2 bg-gray-200 rounded-lg mb-2">
                  <FileText className="h-5 w-5 text-gray-400" />
                </div>
                <p className="text-sm text-muted-foreground text-center">
                  No papers uploaded yet
                </p>
                <p className="text-xs text-muted-foreground text-center mt-1">
                  Upload papers to get started
                </p>
              </div>
            ) : (
              papers.map((paper) => (
                <div
                  key={paper.id}
                  className={`flex items-start gap-2.5 p-2.5 rounded-lg border transition-all cursor-pointer ${
                    selectedPapers.includes(paper.id)
                      ? "bg-primary/5 border-primary/30 shadow-sm"
                      : "bg-white border-transparent hover:bg-gray-50 hover:border-gray-200"
                  }`}
                  onClick={() => handlePaperToggle(paper.id)}
                >
                  <Checkbox
                    id={paper.id}
                    checked={selectedPapers.includes(paper.id)}
                    onCheckedChange={() => handlePaperToggle(paper.id)}
                    className="mt-0.5"
                  />
                  <label
                    htmlFor={paper.id}
                    className="text-sm cursor-pointer flex-1"
                  >
                    <div className="flex items-start gap-2">
                      <FileText className="h-3.5 w-3.5 shrink-0 mt-0.5 text-blue-600" />
                      <span className="line-clamp-2 leading-snug">
                        {paper.title}
                      </span>
                    </div>
                  </label>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Generate Button */}
        <Button
          className="w-full bg-linear-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium shadow-md hover:shadow-lg transition-all h-11"
          onClick={handleGenerate}
          disabled={
            generateMutation.isPending ||
            selectedPapers.length === 0 ||
            !topic.trim()
          }
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              <span>Generating... (30-60s)</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              <span>Generate Literature Review</span>
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
