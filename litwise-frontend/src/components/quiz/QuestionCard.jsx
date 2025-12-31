'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertCircle, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * QuestionCard Component
 * 
 * Displays a single quiz question with:
 * - Question text and metadata
 * - 4 multiple choice options
 * - Visual feedback for selected/correct/incorrect answers
 * - Rationale box when answer is revealed
 * - Difficulty indicator
 * 
 * Props:
 * - question: Question object
 * - questionNumber: Current question number (1-based)
 * - selectedAnswer: User's selected answer index
 * - onSelectAnswer: Callback when user selects an option
 * - isAnswerRevealed: Whether to show correct answer
 * - onRevealAnswer: Callback to reveal answer
 * - totalQuestions: Total questions in quiz
 */
export default function QuestionCard({
    question,
    questionNumber = 1,
    selectedAnswer = null,
    onSelectAnswer,
    isAnswerRevealed = false,
    onRevealAnswer,
    totalQuestions = 1,
}) {
    const [showRationale, setShowRationale] = useState(false);

    // Determine if answer is correct
    const isCorrect = useMemo(() => {
        if (selectedAnswer === null) return null;
        return selectedAnswer === question.correct_answer_index;
    }, [selectedAnswer, question.correct_answer_index]);

    // Get difficulty color
    const difficultyColor = useCallback((difficulty) => {
        switch (difficulty) {
            case 'easy':
                return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
            case 'medium':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
            case 'hard':
                return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    }, []);

    // Get quiz type label
    const getQuizTypeLabel = (type) => {
        return type === 'fact_based' ? 'Fact-Based' : 'Scenario-Based';
    };

    return (
        <div className="w-full space-y-4">
            {/* Header with question number and metadata */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        Question {questionNumber} of {totalQuestions}
                    </span>
                    <div className="h-1.5 w-24 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-500 transition-all duration-300"
                            style={{ width: `${(questionNumber / totalQuestions) * 100}%` }}
                        />
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Badge className={cn('capitalize', difficultyColor(question.difficulty))}>
                        {question.difficulty}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                        {getQuizTypeLabel(question.quiz_type)}
                    </Badge>
                </div>
            </div>

            {/* Question Card */}
            <Card className="shadow-lg border-0 bg-white dark:bg-slate-800">
                <CardHeader className="pb-4">
                    <CardTitle className="text-xl leading-relaxed text-gray-900 dark:text-white">
                        {question.question_text}
                    </CardTitle>
                </CardHeader>

                <CardContent className="space-y-3">
                    {/* Options */}
                    <div className="space-y-2">
                        {question.options.map((option, index) => {
                            const isSelected = selectedAnswer === index;
                            const isCorrectOption = index === question.correct_answer_index;
                            const showCorrect = isAnswerRevealed && isCorrectOption;
                            const showIncorrect = isAnswerRevealed && isSelected && !isCorrect;

                            return (
                                <button
                                    key={index}
                                    onClick={() => {
                                        if (!isAnswerRevealed) {
                                            onSelectAnswer?.(index);
                                        }
                                    }}
                                    disabled={isAnswerRevealed}
                                    className={cn(
                                        'w-full text-left p-4 rounded-lg border-2 transition-all duration-200',
                                        'flex items-start gap-3 cursor-pointer hover:shadow-md',
                                        
                                        // Base styles
                                        !isSelected && !showCorrect && !showIncorrect &&
                                        'border-gray-300 dark:border-gray-600 bg-white dark:bg-slate-700 hover:border-blue-400',
                                        
                                        // Selected but not revealed
                                        isSelected && !isAnswerRevealed &&
                                        'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 shadow-md',
                                        
                                        // Correct answer revealed
                                        showCorrect &&
                                        'border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-900/20 shadow-md',
                                        
                                        // Incorrect answer revealed
                                        showIncorrect &&
                                        'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20 shadow-md',
                                        
                                        // Disabled state
                                        isAnswerRevealed && 'cursor-not-allowed opacity-75'
                                    )}
                                >
                                    {/* Option indicator */}
                                    <div className="shrink-0 mt-1">
                                        {showCorrect ? (
                                            <CheckCircle2 className="w-5 h-5 text-green-500" />
                                        ) : showIncorrect ? (
                                            <XCircle className="w-5 h-5 text-red-500" />
                                        ) : isSelected ? (
                                            <div className="w-5 h-5 rounded-full bg-blue-500 border-2 border-blue-500" />
                                        ) : (
                                            <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                                        )}
                                    </div>

                                    {/* Option text */}
                                    <span className="grow text-gray-900 dark:text-gray-100">
                                        {option}
                                    </span>

                                    {/* Correct indicator */}
                                    {showCorrect && (
                                        <span className="text-xs font-semibold text-green-600 dark:text-green-400 shrink-0">
                                            Correct
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                        {!isAnswerRevealed && selectedAnswer !== null && (
                            <Button
                                onClick={() => {
                                    onRevealAnswer?.();
                                    setShowRationale(true);
                                }}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                            >
                                Show Answer & Rationale
                            </Button>
                        )}

                        {isAnswerRevealed && (
                            <Button
                                onClick={() => setShowRationale(!showRationale)}
                                variant="outline"
                                className="flex-1"
                            >
                                {showRationale ? 'Hide' : 'Show'} Rationale
                                <ChevronDown className={cn(
                                    'w-4 h-4 ml-2 transition-transform',
                                    showRationale && 'rotate-180'
                                )} />
                            </Button>
                        )}

                        {selectedAnswer === null && !isAnswerRevealed && (
                            <div className="flex-1 flex items-center justify-center text-gray-500">
                                <AlertCircle className="w-4 h-4 mr-2" />
                                <span className="text-sm">Select an option to continue</span>
                            </div>
                        )}
                    </div>

                    {/* Rationale Box */}
                    {isAnswerRevealed && showRationale && (
                        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg space-y-3">
                            <h4 className="font-semibold text-blue-900 dark:text-blue-200">
                                Explanation
                            </h4>
                            <p className="text-blue-800 dark:text-blue-100 text-sm leading-relaxed">
                                {question.explanation}
                            </p>

                            {/* Source Citation */}
                            {question.source_citation && (
                                <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
                                    <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
                                        Source:
                                    </p>
                                    <blockquote className="pl-3 border-l-2 border-blue-400 text-xs text-blue-700 dark:text-blue-300 italic">
                                        `{question.source_citation}`
                                    </blockquote>
                                    {question.source_page && (
                                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                                            Page {question.source_page}
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}