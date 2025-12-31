'use client';

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CheckCircle2, AlertTriangle, Lightbulb } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * AnswerFeedback Component
 * 
 * Inline feedback component for answer evaluation
 * Shows immediately after user reveals answer
 * 
 * Props:
 * - isCorrect: Whether answer is correct
 * - explanation: Detailed explanation
 * - hint: Optional learning hint
 */
export default function AnswerFeedback({
    isCorrect,
    explanation,
    hint,
}) {
    if (isCorrect === null) return null;

    return (
        <Alert className={cn(
            'border-2 my-4',
            isCorrect
                ? 'border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-900/20'
                : 'border-red-500 dark:border-red-400 bg-red-50 dark:bg-red-900/20'
        )}>
            <div className="flex gap-3">
                {isCorrect ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
                ) : (
                    <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 space-y-2">
                    <AlertTitle className={cn(
                        isCorrect
                            ? 'text-green-800 dark:text-green-200'
                            : 'text-red-800 dark:text-red-200'
                    )}>
                        {isCorrect ? '✓ Correct!' : '✗ Incorrect'}
                    </AlertTitle>
                    {explanation && (
                        <AlertDescription className={cn(
                            isCorrect
                                ? 'text-green-700 dark:text-green-300'
                                : 'text-red-700 dark:text-red-300'
                        )}>
                            {explanation}
                        </AlertDescription>
                    )}
                    {hint && (
                        <div className="flex gap-2 mt-2 p-2 bg-blue-50 dark:bg-blue-900/30 rounded border-l-2 border-blue-500">
                            <Lightbulb className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                {hint}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </Alert>
    );
}