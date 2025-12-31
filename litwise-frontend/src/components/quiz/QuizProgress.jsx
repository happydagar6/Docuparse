'use client';

import React, { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    CheckCircle2,
    Circle,
    Clock,
    Target,
    TrendingUp,
    Award,
    Navigation
} from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Enhanced QuizProgress Component
 *
 * Features:
 * - Interactive question navigation with animations
 * - Real-time progress visualization
 * - Performance insights and statistics
 * - Smart jump-to-question functionality
 * - Accessibility improvements
 * - Mobile-responsive design
 *
 * Props:
 * - currentQuestion: Current question number (1-based)
 * - totalQuestions: Total questions
 * - answers: Object of answered questions { questionId: answerIndex }
 * - onJumpToQuestion: Callback to jump to specific question
 * - timeRemaining: Optional time remaining for timed quizzes
 * - streakCount: Optional current answer streak
 */
export default function QuizProgress({
    currentQuestion = 1,
    totalQuestions = 1,
    answers = {},
    onJumpToQuestion,
    timeRemaining,
    streakCount = 0,
}) {
    // Enhanced progress calculations
    const progressStats = useMemo(() => {
        const answeredCount = Object.keys(answers).length;
        const unansweredCount = totalQuestions - answeredCount;
        const percentage = Math.round((answeredCount / totalQuestions) * 100);

        // Calculate completion rate
        const completionRate = answeredCount / totalQuestions;

        // Calculate estimated time remaining based on current pace
        const avgTimePerQuestion = timeRemaining ? (timeRemaining / unansweredCount) : null;

        return {
            answered: answeredCount,
            unanswered: unansweredCount,
            percentage,
            completionRate,
            avgTimePerQuestion,
        };
    }, [answers, totalQuestions, timeRemaining]);

    // Get question status for visualization
    const getQuestionStatus = (index) => {
        const questionNum = index + 1;
        const isAnswered = Object.keys(answers).length > index;
        const isCurrent = questionNum === currentQuestion;

        return {
            isAnswered,
            isCurrent,
            status: isCurrent ? 'current' : isAnswered ? 'answered' : 'unanswered'
        };
    };

    // Performance insights
    const performanceInsights = useMemo(() => {
        const answered = Object.keys(answers).length;
        if (answered === 0) return null;

        const recentAnswers = Object.keys(answers).slice(-3); // Last 3 answers
        const hasRecentActivity = recentAnswers.length > 0;

        return {
            hasRecentActivity,
            streakCount,
            isOnStreak: streakCount > 1,
        };
    }, [answers, streakCount]);

    return (
        <div>
            <Card className="bg-white dark:bg-slate-800 border-0 shadow-xl overflow-hidden">
                {/* Header with gradient */}
                <div className="bg-linear-to-r from-blue-600 to-purple-600 p-4 text-white">
                    <div className="flex items-center gap-2 mb-2">
                        <Navigation className="w-5 h-5" />
                        <h3 className="font-semibold text-lg">Quiz Progress</h3>
                    </div>
                    {timeRemaining && (
                        <div className="flex items-center gap-2 text-blue-100">
                            <Clock className="w-4 h-4" />
                            <span className="text-sm font-medium">
                                {Math.floor(timeRemaining / 60)}:{(timeRemaining % 60).toString().padStart(2, '0')} remaining
                            </span>
                        </div>
                    )}
                </div>

                <CardContent className="p-6 space-y-6">
                    {/* Enhanced Progress Section */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                Overall Progress
                            </h4>
                            <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                {progressStats.percentage}%
                            </Badge>
                        </div>

                        <div className="space-y-2">
                            <Progress
                                value={progressStats.percentage}
                                className="h-3 bg-gray-100 dark:bg-gray-700"
                            />
                            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                                <span>{progressStats.answered} answered</span>
                                <span>{progressStats.unanswered} remaining</span>
                            </div>
                        </div>

                        {/* Performance Insights */}
                        {performanceInsights && performanceInsights.isOnStreak && (
                            <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                                <Award className="w-4 h-4 text-green-600 dark:text-green-400" />
                                <span className="text-sm font-medium text-green-800 dark:text-green-200">
                                    {streakCount} answer streak! 🔥
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Enhanced Question Grid */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4" />
                                Questions
                            </h4>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                Click to jump
                            </span>
                        </div>

                        <div className="grid grid-cols-4 sm:grid-cols-5 gap-3">
                            {Array.from({ length: totalQuestions }).map((_, index) => {
                                const questionNum = index + 1;
                                const status = getQuestionStatus(index);

                                return (
                                    <button
                                        key={index}
                                        onClick={() => onJumpToQuestion?.(index)}
                                        className={cn(
                                            'relative aspect-square rounded-xl font-semibold text-sm',
                                            'transition-all duration-300 flex items-center justify-center',
                                            'border-2 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',

                                            // Current question - enhanced styling
                                            status.isCurrent &&
                                            'ring-3 ring-blue-500 dark:ring-blue-400 ring-offset-2 dark:ring-offset-slate-800 bg-blue-500 text-white shadow-lg',

                                            // Answered question
                                            status.isAnswered && !status.isCurrent &&
                                            'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-200 border-green-300 dark:border-green-700 hover:bg-green-200 dark:hover:bg-green-800',

                                            // Unanswered question
                                            !status.isAnswered && !status.isCurrent &&
                                            'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                                        )}
                                        title={`Question ${questionNum} - ${status.status}`}
                                        aria-label={`Go to question ${questionNum}, status: ${status.status}`}
                                    >
                                        {/* Status icon */}
                                        {status.isCurrent ? (
                                            <div className="flex items-center justify-center">
                                                <Target className="w-5 h-5" />
                                            </div>
                                        ) : status.isAnswered ? (
                                            <div className="flex items-center justify-center">
                                                <CheckCircle2 className="w-4 h-4" />
                                            </div>
                                        ) : (
                                            <div className="flex items-center justify-center">
                                                <Circle className="w-4 h-4" />
                                            </div>
                                        )}

                                        {/* Question number overlay */}
                                        <span className={cn(
                                            'absolute -top-1 -right-1 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center',
                                            status.isCurrent
                                                ? 'bg-white text-blue-600'
                                                : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'
                                        )}>
                                            {questionNum}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Quick navigation hints */}
                        <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                                <span>Current question</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-green-100 dark:bg-green-900/40 border border-green-300"></div>
                                <span>Answered</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-gray-50 dark:bg-gray-700 border border-gray-200"></div>
                                <span>Unanswered</span>
                            </div>
                        </div>
                    </div>

                    {/* Enhanced Statistics */}
                    <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                        <div className="grid grid-cols-3 gap-3">
                            <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                                    {progressStats.answered}
                                </div>
                                <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                                    Answered
                                </div>
                            </div>

                            <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                <div className="text-lg font-bold text-gray-600 dark:text-gray-400">
                                    {progressStats.unanswered}
                                </div>
                                <div className="text-xs text-gray-600 dark:text-gray-400 font-medium">
                                    Remaining
                                </div>
                            </div>

                            <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                <div className="text-lg font-bold text-green-600 dark:text-green-400">
                                    {progressStats.percentage}%
                                </div>
                                <div className="text-xs text-green-600 dark:text-green-400 font-medium">
                                    Complete
                                </div>
                            </div>
                        </div>

                        {/* Performance indicator */}
                        {progressStats.completionRate > 0.5 && (
                            <div className="mt-3 p-3 bg-linear-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg border border-green-200 dark:border-green-800">
                                <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                                    <TrendingUp className="w-4 h-4" />
                                    <span className="text-sm font-medium">
                                        Great progress! Keep going! 🚀
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}