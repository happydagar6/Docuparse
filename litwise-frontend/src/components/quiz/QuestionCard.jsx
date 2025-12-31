'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
    CheckCircle2,
    XCircle,
    AlertCircle,
    ChevronDown,
    Lightbulb,
    Clock,
    Target,
    BookOpen,
    Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Enhanced QuestionCard Component
 *
 * Features:
 * - Modern card design with subtle animations
 * - Interactive option selection with hover states
 * - Progressive disclosure for explanations
 * - Visual feedback for correct/incorrect answers
 * - Accessibility improvements
 * - Performance optimizations
 *
 * Props:
 * - question: Question object
 * - questionNumber: Current question number (1-based)
 * - selectedAnswer: User's selected answer index
 * - onSelectAnswer: Callback when user selects an option
 * - isAnswerRevealed: Whether to show correct answer
 * - onRevealAnswer: Callback to reveal answer
 * - totalQuestions: Total questions in quiz
 * - timeSpent: Time spent on this question (optional)
 */
export default function QuestionCard({
    question,
    questionNumber = 1,
    selectedAnswer = null,
    onSelectAnswer,
    isAnswerRevealed = false,
    onRevealAnswer,
    totalQuestions = 1,
    timeSpent,
}) {
    const [showRationale, setShowRationale] = useState(false);

    // Determine if answer is correct
    const isCorrect = useMemo(() => {
        if (selectedAnswer === null) return null;
        return selectedAnswer === question.correct_answer_index;
    }, [selectedAnswer, question.correct_answer_index]);

    // Get difficulty configuration
    const difficultyConfig = useCallback((difficulty) => {
        switch (difficulty) {
            case 'easy':
                return {
                    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 border-green-200',
                    icon: BookOpen,
                    label: 'Easy'
                };
            case 'medium':
                return {
                    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200 border-yellow-200',
                    icon: Target,
                    label: 'Medium'
                };
            case 'hard':
                return {
                    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200 border-red-200',
                    icon: Zap,
                    label: 'Hard'
                };
            default:
                return {
                    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200 border-gray-200',
                    icon: AlertCircle,
                    label: 'Unknown'
                };
        }
    }, []);

    // Get quiz type configuration
    const quizTypeConfig = useCallback((type) => {
        return type === 'fact_based'
            ? { label: 'Fact-Based', icon: BookOpen }
            : { label: 'Scenario-Based', icon: Lightbulb };
    }, []);

    const difficulty = difficultyConfig(question.difficulty);
    const quizType = quizTypeConfig(question.quiz_type);

    // Extract icon components for cleaner JSX
    const DifficultyIcon = difficulty.icon;
    const QuizTypeIcon = quizType.icon;

    return (
        <div className="w-full space-y-6">
            {/* Enhanced Header with Progress */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-full border border-blue-200 dark:border-blue-800">
                            <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                                Question {questionNumber}
                            </span>
                            <span className="text-xs text-blue-600 dark:text-blue-400">
                                of {totalQuestions}
                            </span>
                            </div>
                        {timeSpent && typeof timeSpent === 'number' && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-gray-50 dark:bg-gray-800 rounded-full">
                                <Clock className="w-3 h-3 text-gray-500" />
                                <span className="text-xs text-gray-600 dark:text-gray-400">
                                    {Math.floor(timeSpent / 60)}:{(timeSpent % 60).toString().padStart(2, '0')}
                                </span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        <Badge className={cn('flex items-center gap-1 px-2 py-1', difficulty.color)}>
                            <DifficultyIcon className="w-3 h-3" />
                            {difficulty.label}
                        </Badge>
                        <Badge variant="outline" className="flex items-center gap-1 px-2 py-1">
                            <QuizTypeIcon className="w-3 h-3" />
                            {quizType.label}
                        </Badge>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2">
                    <Progress
                        value={totalQuestions > 0 ? (questionNumber / totalQuestions) * 100 : 0}
                        className="h-2 bg-gray-100 dark:bg-gray-800"
                    />
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                        <span>Progress</span>
                        <span>{totalQuestions > 0 ? Math.round((questionNumber / totalQuestions) * 100) : 0}% Complete</span>
                    </div>
                </div>
            </div>

            {/* Enhanced Question Card */}
            <div className="relative">
                <Card className="shadow-xl border-0 bg-white dark:bg-slate-800 overflow-hidden">
                    {/* Subtle gradient background */}
                    <div className="absolute inset-0 bg-linear-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-900/10 dark:to-purple-900/10" />

                    <CardHeader className="relative pb-6">
                        <CardTitle className="text-xl lg:text-2xl leading-relaxed text-gray-900 dark:text-white font-semibold">
                            {question.question_text}
                        </CardTitle>
                    </CardHeader>

                    <CardContent className="relative space-y-4">
                        {/* Options Grid */}
                        <div className="grid gap-3">
                            {question.options && question.options.length > 0 ? question.options.map((option, index) => {
                                const isSelected = selectedAnswer === index;
                                const isCorrectOption = index === question.correct_answer_index;
                                const showCorrect = isAnswerRevealed && isCorrectOption;
                                const showIncorrect = isAnswerRevealed && isSelected && !isCorrect;

                                return (
                                    <motion.button
                                        key={index}
                                        onClick={() => {
                                            if (!isAnswerRevealed) {
                                                onSelectAnswer?.(index);
                                            }
                                        }}
                                        disabled={isAnswerRevealed}
                                        className={cn(
                                            'group relative w-full text-left p-4 rounded-xl border-2 transition-all duration-300',
                                            'flex items-start gap-4 cursor-pointer overflow-hidden',

                                            // Base styles
                                            !isSelected && !showCorrect && !showIncorrect &&
                                            'border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-700 hover:border-blue-300 hover:shadow-lg hover:-translate-y-0.5',

                                            // Selected but not revealed
                                            isSelected && !isAnswerRevealed &&
                                            'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 shadow-lg ring-2 ring-blue-500/20',

                                            // Correct answer revealed
                                            showCorrect &&
                                            'border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-900/20 shadow-lg ring-2 ring-green-500/20',

                                            // Incorrect answer revealed
                                            showIncorrect &&
                                            'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20 shadow-lg ring-2 ring-red-500/20',

                                            // Disabled state
                                            isAnswerRevealed && 'cursor-not-allowed'
                                        )}
                                    >
                                        {/* Background gradient on hover */}
                                        <div className={cn(
                                            'absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300',
                                            !isAnswerRevealed && 'bg-linear-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20'
                                        )} />

                                        {/* Option indicator */}
                                        <div className="relative z-10 shrink-0 mt-1">
                                            {showCorrect ? (
                                                <motion.div
                                                    initial={{ scale: 0 }}
                                                    animate={{ scale: 1 }}
                                                    className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center"
                                                >
                                                    <CheckCircle2 className="w-4 h-4 text-white" />
                                                </motion.div>
                                            ) : showIncorrect ? (
                                                <motion.div
                                                    initial={{ scale: 0 }}
                                                    animate={{ scale: 1 }}
                                                    className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center"
                                                >
                                                    <XCircle className="w-4 h-4 text-white" />
                                                </motion.div>
                                            ) : isSelected ? (
                                                <motion.div
                                                    initial={{ scale: 0 }}
                                                    animate={{ scale: 1 }}
                                                    className="w-6 h-6 rounded-full bg-blue-500 border-2 border-blue-500 flex items-center justify-center"
                                                >
                                                    <div className="w-2 h-2 rounded-full bg-white" />
                                                </motion.div>
                                            ) : (
                                                <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-gray-600 group-hover:border-blue-400 transition-colors" />
                                            )}
                                        </div>

                                        {/* Option text */}
                                        <span className="relative z-10 grow text-gray-900 dark:text-gray-100 leading-relaxed">
                                            {option}
                                        </span>

                                        {/* Status indicators */}
                                        <AnimatePresence>
                                            {showCorrect && (
                                                <motion.span
                                                    initial={{ opacity: 0, x: 10 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    exit={{ opacity: 0, x: 10 }}
                                                    className="relative z-10 text-sm font-semibold text-green-600 dark:text-green-400 shrink-0"
                                                >
                                                    Correct Answer
                                                </motion.span>
                                            )}
                                        </AnimatePresence>
                                    </motion.button>
                                );
                            }) : (
                                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                                    <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                                    <p>No options available for this question.</p>
                                </div>
                            )}
                        </div>

                        {/* Enhanced Action Section */}
                        <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
                            {!isAnswerRevealed && selectedAnswer !== null && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex gap-3"
                                >
                                    <Button
                                        onClick={() => {
                                            onRevealAnswer?.();
                                            setShowRationale(true);
                                        }}
                                        className="flex-1 bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-all duration-300"
                                        size="lg"
                                    >
                                        <Lightbulb className="w-4 h-4 mr-2" />
                                        Show Answer & Explanation
                                    </Button>
                                </motion.div>
                            )}

                            {isAnswerRevealed && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="space-y-3"
                                >
                                    <Button
                                        onClick={() => setShowRationale(!showRationale)}
                                        variant="outline"
                                        className="w-full border-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-300"
                                        size="lg"
                                    >
                                        <ChevronDown className={cn(
                                            'w-4 h-4 mr-2 transition-transform duration-300',
                                            showRationale && 'rotate-180'
                                        )} />
                                        {showRationale ? 'Hide' : 'Show'} Detailed Explanation
                                    </Button>
                                </motion.div>
                            )}

                            {selectedAnswer === null && !isAnswerRevealed && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex items-center justify-center py-4 text-gray-500 dark:text-gray-400"
                                >
                                    <AlertCircle className="w-5 h-5 mr-2" />
                                    <span className="text-sm font-medium">Select an option to continue</span>
                                </motion.div>
                            )}
                        </div>

                        {/* Enhanced Rationale Section */}
                        <AnimatePresence>
                            {isAnswerRevealed && showRationale && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.3 }}
                                    className="overflow-hidden"
                                >
                                    <div className="mt-6 p-6 bg-linear-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800 rounded-xl space-y-4">
                                        <div className="flex items-center gap-2 mb-3">
                                            <Lightbulb className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                            <h4 className="font-semibold text-blue-900 dark:text-blue-200 text-lg">
                                                Explanation
                                            </h4>
                                        </div>

                                        <p className="text-blue-800 dark:text-blue-100 text-sm leading-relaxed">
                                            {question.explanation || 'No explanation available for this question.'}
                                        </p>

                                        {/* Enhanced Source Citation */}
                                        {question.source_citation && (
                                            <motion.div
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: 0.2 }}
                                                className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800"
                                            >
                                                <div className="flex items-start gap-2">
                                                    <BookOpen className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
                                                    <div>
                                                        <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
                                                            Source Reference:
                                                        </p>
                                                        <blockquote className="pl-3 border-l-2 border-blue-400 text-xs text-blue-700 dark:text-blue-300 italic bg-white/50 dark:bg-slate-800/50 p-2 rounded">
                                                            &quot;{question.source_citation}&quot;
                                                        </blockquote>
                                                        {question.source_page && (
                                                            <p className="text-xs text-blue-600 dark:text-blue-400 mt-2 flex items-center gap-1">
                                                                <Target className="w-3 h-3" />
                                                                Page {question.source_page}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            </motion.div>
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}