'use client';

import React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import QuizConfigForm from '@/components/quiz/QuizConfigForm';
import { useGetUserQuizzes, usePapers } from '@/lib/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Plus, BookOpen, Sparkles, Trophy, Clock, Target } from 'lucide-react';
import { motion } from 'framer-motion';

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

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <motion.div
            className="min-h-screen"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
        >
            {/* Hero Section */}
            <motion.div
                className="relative overflow-hidden bg-linear-to-br from-blue-600 via-purple-600 to-indigo-700 text-white"
                variants={itemVariants}
            >
                <div className="absolute inset-0 bg-black/10" />
                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
                    <div className="text-center">
                        <motion.div
                            className="flex justify-center mb-2"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                        >
                            <div className="p-2 bg-white/10 backdrop-blur-sm rounded-full">
                                <Sparkles className="w-6 h-6" />
                            </div>
                        </motion.div>
                        <motion.h1
                            className="text-xl sm:text-2xl lg:text-3xl font-bold mb-2"
                            variants={itemVariants}
                        >
                            Quiz Generator
                        </motion.h1>
                        <motion.p
                            className="text-sm sm:text-base text-blue-100 max-w-xl mx-auto leading-snug"
                            variants={itemVariants}
                        >
                            Transform your documents into interactive quizzes that test understanding,
                            reinforce learning, and track progress.
                        </motion.p>
                    </div>
                </div>

                {/* Decorative elements */}
                <div className="absolute top-10 left-10 w-20 h-20 bg-white/5 rounded-full blur-xl" />
                <div className="absolute bottom-10 right-10 w-32 h-32 bg-white/5 rounded-full blur-xl" />
                <div className="absolute top-1/2 left-1/4 w-16 h-16 bg-white/5 rounded-full blur-xl" />
            </motion.div>

            {/* Stats Section */}
            <motion.div
                className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800"
                variants={itemVariants}
            >
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="text-center">
                            <div className="flex justify-center mb-2">
                                <Target className="w-8 h-8 text-blue-500" />
                            </div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">
                                {userQuizzes.length}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                Quizzes Created
                            </div>
                        </div>
                        <div className="text-center">
                            <div className="flex justify-center mb-2">
                                <Trophy className="w-8 h-8 text-yellow-500" />
                            </div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">
                                {userQuizzes.reduce((acc, quiz) => acc + (quiz.question_count || 0), 0)}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                Questions Generated
                            </div>
                        </div>
                        <div className="text-center">
                            <div className="flex justify-center mb-2">
                                <Clock className="w-8 h-8 text-green-500" />
                            </div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">
                                {papers.length}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                Documents Available
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="space-y-12">
                    {/* Quiz Configuration Section */}
                    <motion.div variants={itemVariants}>
                        <div className="text-center mb-8">
                            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                                Create Your Quiz
                            </h2>
                            <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                                Customize your quiz parameters and generate an interactive assessment
                                tailored to your learning needs.
                            </p>
                        </div>

                        <QuizConfigForm
                            paperId={paperId}
                            paperTitle={paperTitle}
                            availablePapers={papers}
                            onQuizGenerated={handleQuizGenerated}
                        />
                    </motion.div>

                    {/* Recent Quizzes Section */}
                    <motion.div variants={itemVariants}>
                        <div className="text-center mb-8">
                            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                                Your Quiz Library
                            </h2>
                            <p className="text-lg text-gray-600 dark:text-gray-400">
                                Access your previously created quizzes and track your learning progress.
                            </p>
                        </div>

                        {isLoading ? (
                            <div className="flex items-center justify-center p-12">
                                <div className="text-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
                                    <p className="text-gray-600 dark:text-gray-400">Loading your quizzes...</p>
                                </div>
                            </div>
                        ) : userQuizzes.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {userQuizzes.map((quiz, index) => (
                                    <motion.div
                                        key={quiz.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.1 }}
                                    >
                                        <Card className="group cursor-pointer hover:shadow-xl transition-all duration-300 border-0 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750">
                                            <CardHeader className="pb-3">
                                                <div className="flex items-start justify-between">
                                                    <CardTitle className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                        {quiz.title}
                                                    </CardTitle>
                                                    <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                                        <BookOpen className="w-4 h-4 text-blue-500" />
                                                    </div>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="space-y-4">
                                                {quiz.description && (
                                                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                                        {quiz.description}
                                                    </p>
                                                )}

                                                <div className="flex items-center justify-between text-xs">
                                                    <div className="flex items-center gap-4">
                                                        <div className="flex items-center gap-1">
                                                            <Target className="w-3 h-3 text-gray-400" />
                                                            <span className="text-gray-600 dark:text-gray-400">
                                                                {quiz.question_count} questions
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-1">
                                                            <Trophy className="w-3 h-3 text-gray-400" />
                                                            <span className="text-gray-600 dark:text-gray-400 capitalize">
                                                                {quiz.difficulty_level}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>

                                                <Button
                                                    onClick={() => router.push(`/quiz/${quiz.id}/attempt`)}
                                                    className="w-full bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white border-0"
                                                    size="sm"
                                                >
                                                    <Sparkles className="w-4 h-4 mr-2" />
                                                    Take Quiz
                                                </Button>
                                            </CardContent>
                                        </Card>
                                    </motion.div>
                                ))}
                            </div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.2 }}
                            >
                                <Card className="bg-linear-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border-dashed border-2 border-gray-300 dark:border-gray-600">
                                    <CardContent className="py-16 text-center">
                                        <div className="mb-6">
                                            <div className="p-4 bg-gray-200 dark:bg-gray-700 rounded-full w-fit mx-auto mb-4">
                                                <BookOpen className="w-8 h-8 text-gray-500 dark:text-gray-400" />
                                            </div>
                                            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                                                No Quizzes Yet
                                            </h3>
                                            <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
                                                Create your first quiz using the form above to start testing your knowledge
                                                and tracking your learning progress.
                                            </p>
                                        </div>
                                        <div className="flex justify-center">
                                            <div className="animate-bounce">
                                                <Sparkles className="w-6 h-6 text-blue-500" />
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        )}
                    </motion.div>
                </div>
            </div>
        </motion.div>
    );
}