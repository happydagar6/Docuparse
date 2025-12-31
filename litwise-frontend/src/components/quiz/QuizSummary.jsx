'use client';

import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
    Trophy, 
    Target, 
    TrendingUp, 
    AlertCircle, 
    BookOpen,
    CheckCircle2,
    XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * QuizSummary Component
 * 
 * Displays comprehensive quiz results:
 * - Overall score with visual feedback
 * - Performance metrics
 * - Weak areas that need review
 * - Recommendations for improvement
 * 
 * Props:
 * - quiz: Quiz object with questions
 * - answers: User's answers
 * - onRetakeQuiz: Callback to retake
 * - onBackHome: Callback to go back
 */
export default function QuizSummary({
    quiz,
    answers = {},
    onRetakeQuiz,
    onBackHome,
}) {
    // Calculate detailed results
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
            };
        });

        const correct = questionResults.filter(r => r.isCorrect).length;
        const total = questionResults.length;
        const percentage = Math.round((correct / total) * 100);

        // Categorize by difficulty
        const byDifficulty = {
            easy: questionResults.filter(r => r.difficulty === 'easy'),
            medium: questionResults.filter(r => r.difficulty === 'medium'),
            hard: questionResults.filter(r => r.difficulty === 'hard'),
        };

        // Calculate performance by difficulty
        const performanceByDifficulty = {
            easy: byDifficulty.easy.length > 0 
                ? Math.round((byDifficulty.easy.filter(r => r.isCorrect).length / byDifficulty.easy.length) * 100)
                : null,
            medium: byDifficulty.medium.length > 0
                ? Math.round((byDifficulty.medium.filter(r => r.isCorrect).length / byDifficulty.medium.length) * 100)
                : null,
            hard: byDifficulty.hard.length > 0
                ? Math.round((byDifficulty.hard.filter(r => r.isCorrect).length / byDifficulty.hard.length) * 100)
                : null,
        };

        // Weak areas (questions answered incorrectly)
        const weakAreas = questionResults
            .filter(r => !r.isCorrect && r.isAnswered)
            .slice(0, 5); // Top 5 weak areas

        // Identify topics to review
        const topicsToReview = weakAreas.map(area => ({
            topic: area.question.substring(0, 100),
            difficulty: area.difficulty,
            explanation: area.explanation,
        }));

        return {
            correct,
            total,
            percentage,
            questionResults,
            byDifficulty,
            performanceByDifficulty,
            weakAreas,
            topicsToReview,
        };
    }, [quiz.questions, answers]);

    if (!results) return null;

    // Get performance rating
    const getPerformanceRating = (percentage) => {
        if (percentage >= 90) return { label: 'Excellent', color: 'text-green-600', icon: '🏆' };
        if (percentage >= 80) return { label: 'Good', color: 'text-blue-600', icon: '👍' };
        if (percentage >= 70) return { label: 'Satisfactory', color: 'text-yellow-600', icon: '👌' };
        if (percentage >= 60) return { label: 'Needs Improvement', color: 'text-orange-600', icon: '📚' };
        return { label: 'Poor', color: 'text-red-600', icon: '⚠️' };
    };

    const rating = getPerformanceRating(results.percentage);

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            {/* Main Score Card */}
            <Card className="bg-linear-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-0 shadow-lg">
                <CardContent className="p-8 text-center space-y-4">
                    <div className="text-6xl mb-2">{rating.icon}</div>
                    <div className="space-y-2">
                        <h2 className={cn(
                            'text-4xl font-bold',
                            rating.color
                        )}>
                            {results.percentage}%
                        </h2>
                        <p className={cn('text-lg font-semibold', rating.color)}>
                            {rating.label}
                        </p>
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-lg p-4 inline-block">
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                            {results.correct} out of {results.total} correct
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Performance by Difficulty */}
            <Card className="border-0 shadow-md">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Target className="w-5 h-5" />
                        Performance by Difficulty
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {['easy', 'medium', 'hard'].map(difficulty => (
                        results.performanceByDifficulty[difficulty] !== null && (
                            <div key={difficulty} className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="capitalize font-medium text-gray-700 dark:text-gray-300">
                                            {difficulty}
                                        </span>
                                        <span className="text-sm text-gray-500">
                                            ({results.byDifficulty[difficulty].length} questions)
                                        </span>
                                    </div>
                                    <span className="font-bold text-gray-900 dark:text-white">
                                        {results.performanceByDifficulty[difficulty]}%
                                    </span>
                                </div>
                                <Progress 
                                    value={results.performanceByDifficulty[difficulty]}
                                    className="h-2"
                                />
                            </div>
                        )
                    ))}
                </CardContent>
            </Card>

            {/* Weak Areas Review */}
            {results.weakAreas.length > 0 && (
                <Card className="border-2 border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/10">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-yellow-700 dark:text-yellow-200">
                            <AlertCircle className="w-5 h-5" />
                            Topics to Review
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {results.topicsToReview.map((topic, index) => (
                            <div key={index} className="p-4 bg-white dark:bg-slate-800 rounded-lg border-l-4 border-yellow-500 space-y-2">
                                <div className="flex items-start justify-between gap-2">
                                    <p className="font-medium text-gray-900 dark:text-white flex-1">
                                        {topic.topic}...
                                    </p>
                                    <Badge className="capitalize bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                                        {topic.difficulty}
                                    </Badge>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {topic.explanation}
                                </p>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}

            {/* Question Review Summary */}
            <Card className="border-0 shadow-md">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <BookOpen className="w-5 h-5" />
                        Question Review
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        {results.questionResults.map((result, index) => (
                            <div 
                                key={index} 
                                className={cn(
                                    'p-3 rounded-lg flex items-center gap-3 border',
                                    result.isCorrect
                                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                                )}
                            >
                                {result.isCorrect ? (
                                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
                                ) : (
                                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0" />
                                )}
                                <div className="flex-1 min-w-0">
                                    <p className={cn(
                                        'text-sm font-medium truncate',
                                        result.isCorrect
                                            ? 'text-green-900 dark:text-green-100'
                                            : 'text-red-900 dark:text-red-100'
                                    )}>
                                        Q{index + 1}: {result.question.substring(0, 60)}...
                                    </p>
                                </div>
                                <Badge className={cn(
                                    'capitalize',
                                    result.isCorrect
                                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                )}>
                                    {result.difficulty}
                                </Badge>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="flex gap-3 justify-center">
                <Button
                    onClick={onRetakeQuiz}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-8"
                >
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Retake Quiz
                </Button>
                <Button
                    onClick={onBackHome}
                    variant="outline"
                    className="px-8"
                >
                    Back to Home
                </Button>
            </div>
        </div>
    );
}