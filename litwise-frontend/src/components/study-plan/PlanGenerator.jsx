"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { getPapers } from "@/lib/api";
import { generateStudyPlan } from "@/app/api/study-plan";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Slider } from "../ui/slider";
import { Button } from "../ui/button";
import { 
  Brain, 
  BookOpen, 
  Loader2, 
  Calendar, 
  Clock, 
  GraduationCap, 
  Zap, 
  Scale, 
  Coffee, 
  Sparkles,
  FileText,
  Trophy
} from "lucide-react";

const EXAM_TYPES = [
  { value: "school_test", label: "School Test", icon: BookOpen, color: "text-blue-500" },
  { value: "college_exam", label: "College Exam", icon: GraduationCap, color: "text-purple-500" },
  { value: "competitive", label: "Competitive", icon: Trophy, color: "text-orange-500" },
  { value: "certification", label: "Certification", icon: FileText, color: "text-green-500" },
];

const STUDY_STYLES = [
  { value: "intensive", label: "Intensive", icon: Zap, color: "text-red-500" },
  { value: "balanced", label: "Balanced", icon: Scale, color: "text-blue-500" },
  { value: "light", label: "Light", icon: Coffee, color: "text-green-500" },
];

export default function PlanGenerator({ onPlanGenerated }) {
  const [formData, setFormData] = useState({
    paper_id: "",
    duration_weeks: 4,
    exam_type: "college_exam",
    study_style: "balanced",
    daily_hours: 2,
  });

  const { data: papersdata, isLoading: loadingPapers } = useQuery({
    queryKey: ["papers"],
    queryFn: getPapers,
  });

  const mutation = useMutation({
    mutationFn: generateStudyPlan,
    onSuccess: (data) => {
      toast.success("Study plan generated successfully!");
      onPlanGenerated?.(data);
    },
    onError: () =>
      toast.error("Failed to generate study plan. Please try again."),
  });

  // Backend returns array directly, not { papers: [...] }
  // Status is 'completed' not 'processed'
  const papers =
    (Array.isArray(papersdata) ? papersdata : papersdata?.papers || [])
      .filter((p) => p.processing_status === "completed");

  const selectedPaper = papers.find(p => p.id === formData.paper_id);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.paper_id) {
      toast.error("Please select a paper to generate a study plan.");
      return;
    }
    mutation.mutate(formData); // Trigger the mutation
  };

  return (
    <Card className="overflow-hidden border-0 shadow-lg bg-gradient-to-br from-white to-slate-50/50">
      <CardHeader className="bg-gradient-to-r from-teal-500 to-cyan-500 text-white pb-4">
        <CardTitle className="flex items-center gap-2">
          <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
            <Brain className="h-5 w-5" />
          </div>
          <div>
            <span className="text-lg font-semibold">AI Study Planner</span>
            <p className="text-xs font-normal text-white/80 mt-0.5">Generate personalized schedules</p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Document Select */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-teal-500" />
              Select Document
            </label>
            <Select
              value={formData.paper_id}
              onValueChange={(v) => setFormData((p) => ({ ...p, paper_id: v }))}
            >
              <SelectTrigger className="h-11 border-2 hover:border-teal-300 transition-colors">
                <SelectValue placeholder="Choose a document..." />
              </SelectTrigger>
              <SelectContent>
                {papers.map((paper) => (
                  <SelectItem key={paper.id} value={paper.id}>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-100 to-cyan-100 flex items-center justify-center">
                        <FileText className="h-3.5 w-3.5 text-teal-600" />
                      </div>
                      <span className="truncate max-w-[180px] font-medium">
                        {paper.title}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <AnimatePresence>
              {selectedPaper && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-2.5 bg-teal-50 rounded-lg border border-teal-100 mt-1">
                    <p className="text-xs text-teal-700 font-medium truncate">📄 {selectedPaper.title}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            {papers.length === 0 && !loadingPapers && (
              <p className="text-xs text-amber-600 bg-amber-50 p-2 rounded-lg">
                ⚠️ No processed documents. Upload and process a document first.
              </p>
            )}
          </div>

          {/* Duration Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium flex items-center gap-2">
                <Calendar className="h-4 w-4 text-teal-500" />
                Study Duration
              </label>
              <Badge variant="secondary" className="bg-teal-100 text-teal-700 font-semibold">
                {formData.duration_weeks} {formData.duration_weeks === 1 ? 'week' : 'weeks'}
              </Badge>
            </div>
            <Slider
              value={[formData.duration_weeks]}
              onValueChange={([v]) =>
                setFormData((p) => ({ ...p, duration_weeks: v }))
              }
              min={1}
              max={12}
              step={1}
              className="cursor-pointer"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1 week</span>
              <span className="text-teal-600 font-medium">Optimal: 4-6 weeks</span>
              <span>12 weeks</span>
            </div>
          </div>

          {/* Daily Hours Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4 text-teal-500" />
                Daily Study Hours
              </label>
              <Badge variant="secondary" className="bg-cyan-100 text-cyan-700 font-semibold">
                {formData.daily_hours} {formData.daily_hours === 1 ? 'hour' : 'hours'}/day
              </Badge>
            </div>
            <Slider
              value={[formData.daily_hours]}
              onValueChange={([v]) =>
                setFormData((p) => ({ ...p, daily_hours: v }))
              }
              min={1}
              max={8}
              step={1}
              className="cursor-pointer"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1 hour</span>
              <span className="text-cyan-600 font-medium">Recommended: 2-4 hrs</span>
              <span>8 hours</span>
            </div>
          </div>

          {/* Exam Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <GraduationCap className="h-4 w-4 text-teal-500" />
              Exam Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              {EXAM_TYPES.map((type) => {
                const Icon = type.icon;
                const isSelected = formData.exam_type === type.value;
                return (
                  <motion.button
                    key={type.value}
                    type="button"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setFormData((p) => ({ ...p, exam_type: type.value }))}
                    className={`p-3 rounded-xl border-2 text-left transition-all duration-200 ${isSelected ? 'border-teal-500 bg-teal-50 shadow-md' : 'border-gray-200 hover:border-gray-300 bg-white'}`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`h-4 w-4 ${isSelected ? 'text-teal-600' : type.color}`} />
                      <span className={`text-sm font-medium ${isSelected ? 'text-teal-700' : 'text-gray-700'}`}>{type.label}</span>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </div>

          {/* Study Style */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-500" />
              Study Style
            </label>
            <div className="grid grid-cols-3 gap-2">
              {STUDY_STYLES.map((style) => {
                const Icon = style.icon;
                const isSelected = formData.study_style === style.value;
                return (
                  <motion.button
                    key={style.value}
                    type="button"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setFormData((p) => ({ ...p, study_style: style.value }))}
                    className={`p-3 rounded-xl border-2 text-center transition-all duration-200 ${isSelected ? 'border-teal-500 bg-teal-50 shadow-md' : 'border-gray-200 hover:border-gray-300 bg-white'}`}
                  >
                    <Icon className={`h-5 w-5 mx-auto mb-1 ${isSelected ? 'text-teal-600' : style.color}`} />
                    <span className={`text-xs font-medium block ${isSelected ? 'text-teal-700' : 'text-gray-700'}`}>{style.label}</span>
                  </motion.button>
                );
              })}
            </div>
          </div>
          <motion.div whileHover={{ scale: mutation.isPending ? 1 : 1.01 }} whileTap={{ scale: mutation.isPending ? 1 : 0.99 }}>
            <Button 
              type="submit" 
              className="w-full h-12 bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 text-white font-medium shadow-lg shadow-teal-200 transition-all duration-300" 
              disabled={mutation.isPending || !formData.paper_id}
            >
              {mutation.isPending ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Creating Your Plan...</span>
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  <span>Generate Study Plan</span>
                </span>
              )}
            </Button>
          </motion.div>
        </form>
      </CardContent>
    </Card>
  );
}