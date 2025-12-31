'use client';

import React, { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * QuizProgress Component
 * 
 * Displays:
 * - Overall progress bar
 * - Question grid showing answered/unanswered
 * - Progress statistics
 * 
 * Props:
 * - currentQuestion: Current question number (1-based)
 * - totalQuestions: Total questions
 * - answers: Object of answered questions { questionId: answerIndex }
 * - onJumpToQuestion: Callback to jump to specific question
 */
export default function QuizProgress({
    currentQuestion = 1,
    totalQuestions = 1,
    answers = {},
    onJumpToQuestion,
}) {
    // Calculate progress stats
    const stats = useMemo(() => {
        const answered = Object.keys(answers).length;
        const unanswered = totalQuestions - answered;
        const percentage = Math.round((answered / totalQuestions) * 100);

        return {
            answered,
            unanswered,
            percentage,
        };
    }, [answers, totalQuestions]);

    return (
        <Card className="bg-white dark:bg-slate-800 border-0 shadow-md">
            <CardContent className="p-6 space-y-6">
                {/* Overall Progress Bar */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                            Overall Progress
                        </h3>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            {stats.answered} of {totalQuestions} answered
                        </span>
                    </div>
                    <Progress 
                        value={stats.percentage} 
                        className="h-3"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        {stats.percentage}% Complete • {stats.unanswered} remaining
                    </p>
                </div>

                {/* Question Grid */}
                <div className="space-y-3">
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                        Questions
                    </h3>
                    <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-8 gap-2">
                        {Array.from({ length: totalQuestions }).map((_, index) => {
                            const questionNum = index + 1;
                            const isAnswered = Object.keys(answers).length > index;
                            const isCurrent = questionNum === currentQuestion;

                            return (
                                <button
                                    key={index}
                                    onClick={() => onJumpToQuestion?.(index)}
                                    className={cn(
                                        'relative w-full aspect-square rounded-lg font-medium text-sm',
                                        'transition-all duration-200 flex items-center justify-center',
                                        
                                        // Current question
                                        isCurrent &&
                                        'ring-2 ring-blue-500 dark:ring-blue-400',
                                        
                                        // Answered
                                        isAnswered && !isCurrent &&
                                        'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-200 hover:bg-green-200',
                                        
                                        // Unanswered
                                        !isAnswered && !isCurrent &&
                                        'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200',
                                        
                                        // Base current styling
                                        isCurrent &&
                                        'bg-blue-500 text-white dark:bg-blue-600 hover:bg-blue-600'
                                    )}
                                    title={`Question ${questionNum}`}
                                >
                                    {isAnswered ? (
                                        <CheckCircle2 className="w-4 h-4" />
                                    ) : (
                                        <Circle className="w-4 h-4" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="text-center">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Answered</p>
                        <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            {stats.answered}
                        </Badge>
                    </div>
                    <div className="text-center">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Unanswered</p>
                        <Badge variant="outline" className="bg-gray-100 dark:bg-gray-700">
                            {stats.unanswered}
                        </Badge>
                    </div>
                    <div className="text-center">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Progress</p>
                        <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            {stats.percentage}%
                        </Badge>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}