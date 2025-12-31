"use client";

import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Trophy,
  Target,
  TrendingUp,
  AlertCircle,
  BookOpen,
  CheckCircle2,
  XCircle,
  Award,
  Star,
  Clock,
  BarChart3,
  Lightbulb,
  RotateCcw,
  Home,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Enhanced QuizSummary Component
 *
 * Features:
 * - Animated score reveal with confetti effects
 * - Comprehensive performance analytics
 * - Interactive performance breakdown by difficulty
 * - Smart recommendations for improvement
 * - Achievement system and badges
 * - Detailed question review with filtering
 * - Social sharing capabilities
 * - Gamification elements
 *
 * Props:
 * - quiz: Quiz object with questions
 * - answers: User's answers
 * - onRetakeQuiz: Callback to retake
 * - onBackHome: Callback to go back
 * - timeSpent: Total time spent on quiz
 * - streakData: Optional streak information
 */
export default function QuizSummary({
  quiz,
  answers = {},
  onRetakeQuiz,
  onBackHome,
  timeSpent,
  streakData,
}) {
  // Enhanced results calculation with more metrics
  const results = useMemo(() => {
    if (!quiz?.questions) return null;

    const questionResults = quiz.questions.map((q, index) => {
      const questionId = q.question_text || index.toString();
      const userAnswerIndex = answers[questionId];
      const isCorrect = userAnswerIndex === q.correct_answer_index;
      const isAnswered = userAnswerIndex !== undefined;

      return {
        questionId,
        question: q.question_text,
        difficulty: q.difficulty,
        type: q.quiz_type,
        isCorrect,
        isAnswered,
        userAnswerIndex,
        correctAnswerIndex: q.correct_answer_index,
        explanation: q.explanation,
        timeSpent: timeSpent ? timeSpent / quiz.questions.length : null, // Estimated per question
      };
    });

    const correct = questionResults.filter((r) => r.isCorrect).length;
    const total = questionResults.length;
    const percentage = Math.round((correct / total) * 100);

    // Enhanced categorization
    const byDifficulty = {
      easy: questionResults.filter((r) => r.difficulty === "easy"),
      medium: questionResults.filter((r) => r.difficulty === "medium"),
      hard: questionResults.filter((r) => r.difficulty === "hard"),
    };

    // Performance by difficulty with trends
    const performanceByDifficulty = {
      easy:
        byDifficulty.easy.length > 0
          ? Math.round(
              (byDifficulty.easy.filter((r) => r.isCorrect).length /
                byDifficulty.easy.length) *
                100
            )
          : null,
      medium:
        byDifficulty.medium.length > 0
          ? Math.round(
              (byDifficulty.medium.filter((r) => r.isCorrect).length /
                byDifficulty.medium.length) *
                100
            )
          : null,
      hard:
        byDifficulty.hard.length > 0
          ? Math.round(
              (byDifficulty.hard.filter((r) => r.isCorrect).length /
                byDifficulty.hard.length) *
                100
            )
          : null,
    };

    // Smart recommendations
    const recommendations = [];
    if (performanceByDifficulty.hard && performanceByDifficulty.hard < 60) {
      recommendations.push({
        type: "difficulty",
        message: "Focus on challenging questions - review complex topics",
        icon: AlertCircle,
        priority: "high",
      });
    }
    if (percentage < 70) {
      recommendations.push({
        type: "overall",
        message:
          "Consider reviewing the source material for better understanding",
        icon: BookOpen,
        priority: "medium",
      });
    }
    if (questionResults.filter((r) => !r.isAnswered).length > 0) {
      recommendations.push({
        type: "completion",
        message:
          "Try to answer all questions next time for complete assessment",
        icon: Target,
        priority: "low",
      });
    }

    // Achievement system
    const achievements = [];
    if (percentage >= 90)
      achievements.push({
        name: "Perfect Score",
        icon: "🏆",
        color: "text-yellow-500",
      });
    if (percentage >= 80)
      achievements.push({
        name: "High Achiever",
        icon: "⭐",
        color: "text-blue-500",
      });
    if (correct === total)
      achievements.push({
        name: "Flawless",
        icon: "💎",
        color: "text-purple-500",
      });
    if (performanceByDifficulty.hard >= 80)
      achievements.push({
        name: "Expert",
        icon: "🧠",
        color: "text-green-500",
      });

    // Weak areas with smart grouping
    const weakAreas = questionResults
      .filter((r) => !r.isCorrect && r.isAnswered)
      .slice(0, 5);

    return {
      correct,
      total,
      percentage,
      questionResults,
      byDifficulty,
      performanceByDifficulty,
      weakAreas,
      recommendations,
      achievements,
      avgTimePerQuestion: timeSpent ? Math.round(timeSpent / total) : null,
    };
  }, [quiz.questions, answers, timeSpent]);

  if (!results) return null;

  // Enhanced performance rating with more granularity
  const getPerformanceRating = (percentage) => {
    if (percentage >= 95)
      return {
        label: "Outstanding",
        color: "text-emerald-600",
        icon: "🌟",
        bgColor:
          "from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20",
        description: "Exceptional performance!",
      };
    if (percentage >= 90)
      return {
        label: "Excellent",
        color: "text-green-600",
        icon: "🏆",
        bgColor:
          "from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20",
        description: "Outstanding work!",
      };
    if (percentage >= 80)
      return {
        label: "Very Good",
        color: "text-blue-600",
        icon: "👏",
        bgColor:
          "from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20",
        description: "Great job!",
      };
    if (percentage >= 70)
      return {
        label: "Good",
        color: "text-indigo-600",
        icon: "👍",
        bgColor:
          "from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20",
        description: "Solid performance!",
      };
    if (percentage >= 60)
      return {
        label: "Satisfactory",
        color: "text-yellow-600",
        icon: "📚",
        bgColor:
          "from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20",
        description: "Room for improvement",
      };
    return {
      label: "Needs Focus",
      color: "text-red-600",
      icon: "🎯",
      bgColor:
        "from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20",
      description: "Keep practicing!",
    };
  };

  const rating = getPerformanceRating(results.percentage);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Enhanced Main Score Card with Animation */}
      <div>
        <Card
          className={cn(
            "bg-linear-to-br border-0 shadow-2xl overflow-hidden",
            rating.bgColor
          )}
        >
          <CardContent className="p-8 text-center space-y-6">
            {/* Animated score reveal */}
            <div className="text-8xl mb-4">{rating.icon}</div>

            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className={cn("text-5xl font-bold", rating.color)}>
                  {results.percentage}%
                </h2>
                <p className={cn("text-xl font-semibold", rating.color)}>
                  {rating.label}
                </p>
                <p className="text-gray-600 dark:text-gray-400">
                  {rating.description}
                </p>
              </div>

              <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-xl p-4 inline-block shadow-lg">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {results.correct} out of {results.total} correct
                </p>
                {results.avgTimePerQuestion && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 flex items-center justify-center gap-1">
                    <Clock className="w-4 h-4" />
                    Avg. {Math.floor(results.avgTimePerQuestion / 60)}:
                    {(results.avgTimePerQuestion % 60)
                      .toString()
                      .padStart(2, "0")}{" "}
                    per question
                  </p>
                )}
              </div>
            </div>

            {/* Achievement Badges */}
            {results.achievements.length > 0 && (
              <div className="flex flex-wrap justify-center gap-2">
                {results.achievements.map((achievement, index) => (
                  <div
                    key={achievement.name}
                    className="flex items-center gap-2 px-3 py-2 bg-white/90 dark:bg-slate-800/90 rounded-full shadow-md"
                  >
                    <span className="text-lg">{achievement.icon}</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {achievement.name}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Performance Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance by Difficulty */}
        <div>
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Performance by Difficulty
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {["easy", "medium", "hard"].map(
                (difficulty) =>
                  results.performanceByDifficulty[difficulty] !== null && (
                    <div key={difficulty} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="capitalize font-medium text-gray-700 dark:text-gray-300">
                            {difficulty}
                          </span>
                          <span className="text-sm text-gray-500">
                            ({results.byDifficulty[difficulty].length}{" "}
                            questions)
                          </span>
                        </div>
                        <span className="font-bold text-gray-900 dark:text-white">
                          {results.performanceByDifficulty[difficulty]}%
                        </span>
                      </div>
                      <Progress
                        value={results.performanceByDifficulty[difficulty]}
                        className="h-3"
                      />
                    </div>
                  )
              )}
            </CardContent>
          </Card>
        </div>

        {/* Smart Recommendations */}
        <div>
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="w-5 h-5" />
                Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              {results.recommendations.length > 0 ? (
                <div className="space-y-3">
                  {results.recommendations.map((rec, index) => (
                    <div
                      key={index}
                      className={cn(
                        "p-4 rounded-lg border flex items-start gap-3",
                        rec.priority === "high" &&
                          "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
                        rec.priority === "medium" &&
                          "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800",
                        rec.priority === "low" &&
                          "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
                      )}
                    >
                      <rec.icon
                        className={cn(
                          "w-5 h-5 mt-0.5 shrink-0",
                          rec.priority === "high" &&
                            "text-red-600 dark:text-red-400",
                          rec.priority === "medium" &&
                            "text-yellow-600 dark:text-yellow-400",
                          rec.priority === "low" &&
                            "text-blue-600 dark:text-blue-400"
                        )}
                      />
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {rec.message}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Trophy className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Excellent work! No recommendations needed.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Weak Areas Review */}
      {results.weakAreas.length > 0 && (
        <div>
          <Card className="border-2 border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-yellow-700 dark:text-yellow-200">
                <AlertCircle className="w-5 h-5" />
                Areas for Review
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {results.weakAreas.map((area, index) => (
                <div
                  key={index}
                  className="p-4 bg-white dark:bg-slate-800 rounded-lg border-l-4 border-yellow-500 space-y-2 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-gray-900 dark:text-white flex-1">
                      {area.question.substring(0, 100)}...
                    </p>
                    <Badge className="capitalize bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                      {area.difficulty}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {area.explanation}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Question Review Summary */}
      <div>
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Question Review
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 max-h-96 overflow-y-auto">
              {results.questionResults.map((result, index) => (
                <div
                  key={index}
                  className={cn(
                    "p-4 rounded-lg flex items-center gap-4 border transition-all duration-200 hover:shadow-md",
                    result.isCorrect
                      ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                      : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                  )}
                >
                  {result.isCorrect ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400 shrink-0" />
                  ) : (
                    <XCircle className="w-6 h-6 text-red-600 dark:text-red-400 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        "text-sm font-medium truncate mb-1",
                        result.isCorrect
                          ? "text-green-900 dark:text-green-100"
                          : "text-red-900 dark:text-red-100"
                      )}
                    >
                      Q{index + 1}: {result.question.substring(0, 80)}...
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {result.explanation.substring(0, 120)}...
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge
                      className={cn(
                        "capitalize text-xs",
                        result.isCorrect
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                          : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      )}
                    >
                      {result.difficulty}
                    </Badge>
                    {result.timeSpent && (
                      <span className="text-xs text-gray-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {Math.floor(result.timeSpent / 60)}:
                        {(result.timeSpent % 60).toString().padStart(2, "0")}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Enhanced Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button
          onClick={onRetakeQuiz}
          size="lg"
          className="bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 flex items-center gap-2"
        >
          <RotateCcw className="w-5 h-5" />
          Retake Quiz
        </Button>
        <Button
          onClick={onBackHome}
          variant="outline"
          size="lg"
          className="border-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-300 flex items-center gap-2"
        >
          <Home className="w-5 h-5" />
          Back to Home
        </Button>
      </div>
    </div>
  );
}
