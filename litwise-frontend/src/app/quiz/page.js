'use client';

import React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import QuizConfigForm from '@/components/quiz/QuizConfigForm';
import { useGetUserQuizzes, usePapers } from '@/lib/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Plus, BookOpen } from 'lucide-react';

export default function QuizPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const paperId = searchParams.get('paperId');
    const paperTitle = searchParams.get('paperTitle');
    const { data: userQuizzes = [], isLoading } = useGetUserQuizzes();
    const { data: papers = [], isLoading: papersLoading } = usePapers();

    const handleQuizGenerated = (quiz) => {
        // Redirect to quiz attempt page
        router.push(`/quiz/${quiz.id}/attempt`);
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white">Quiz Generator</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    Generate interactive quizzes from your documents to test your understanding
                </p>
            </div>

            {/* Config Form - Pass paperId, paperTitle, and availablePapers */}
            <QuizConfigForm 
                paperId={paperId}
                paperTitle={paperTitle}
                availablePapers={papers}
                onQuizGenerated={handleQuizGenerated} 
            />

            {/* Recent Quizzes */}
            <div className="mt-12">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                        Your Recent Quizzes
                    </h2>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center p-8">
                        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                    </div>
                ) : userQuizzes.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {userQuizzes.map(quiz => (
                            <Card key={quiz.id} className="cursor-pointer hover:shadow-lg transition-shadow">
                                <CardHeader>
                                    <CardTitle className="text-lg">{quiz.title}</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <p className="text-sm text-gray-600">{quiz.description}</p>
                                    <div className="flex items-center justify-between text-xs text-gray-500">
                                        <span>{quiz.question_count} questions</span>
                                        <span className="capitalize">{quiz.difficulty_level}</span>
                                    </div>
                                    <Button
                                        onClick={() => router.push(`/quiz/${quiz.id}/attempt`)}
                                        className="w-full"
                                        variant="outline"
                                    >
                                        Take Quiz
                                    </Button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <Card className="bg-slate-50 dark:bg-slate-800 border-dashed">
                        <CardContent className="py-12 text-center">
                            <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-600 dark:text-gray-400">
                                No quizzes yet. Generate your first quiz above!
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}