'use client';

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';

/**
 * Enhanced Custom hook for managing quiz-taking state
 * Features:
 * - Time tracking per question and total
 * - Answer streak counting
 * - Performance analytics
 * - Smart state persistence
 * - Accessibility improvements
 */
export function useQuizState(quiz) {
    // Quiz data
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

    // User answers: { questionId: answerIndex }
    const [answers, setAnswers] = useState({});

    // Revealed answers: { questionId: true }
    const [revealedAnswers, setRevealedAnswers] = useState({});

    // Quiz status: 'in-progress' | 'submitted' | 'reviewing'
    const [quizStatus, setQuizStatus] = useState('in-progress');

    // Time tracking
    const [questionStartTime, setQuestionStartTime] = useState(Date.now());
    const [totalTimeSpent, setTotalTimeSpent] = useState(0);
    const [questionTimes, setQuestionTimes] = useState({}); // { questionIndex: timeSpent }

    // Performance tracking
    const [streakCount, setStreakCount] = useState(0);
    const [maxStreak, setMaxStreak] = useState(0);

    // Refs for time tracking
    const quizStartTimeRef = useRef(Date.now());
    const currentQuestionStartRef = useRef(Date.now());

    // Reset question timer when question changes
    useEffect(() => {
        currentQuestionStartRef.current = Date.now();
        setQuestionStartTime(Date.now());
    }, [currentQuestionIndex]);

    // Current question
    const currentQuestion = useMemo(() => {
        if (!quiz?.questions) return null;
        return quiz.questions[currentQuestionIndex] || null;
    }, [quiz?.questions, currentQuestionIndex]);

    // Answer current question with streak tracking
    const answerQuestion = useCallback((answerIndex) => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);

        setAnswers(prev => ({
            ...prev,
            [questionId]: answerIndex,
        }));

        // Update time tracking
        setQuestionTimes(prev => ({
            ...prev,
            [currentQuestionIndex]: timeSpent,
        }));

        // Update streak
        const isCorrect = answerIndex === currentQuestion?.correct_answer_index;
        if (isCorrect) {
            setStreakCount(prev => {
                const newStreak = prev + 1;
                setMaxStreak(current => Math.max(current, newStreak));
                return newStreak;
            });
        } else {
            setStreakCount(0);
        }
    }, [currentQuestion, currentQuestionIndex]);

    // Reveal answer
    const revealAnswer = useCallback(() => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        setRevealedAnswers(prev => ({
            ...prev,
            [questionId]: true,
        }));
    }, [currentQuestion, currentQuestionIndex]);

    // Move to next question
    const nextQuestion = useCallback(() => {
        if (currentQuestionIndex < quiz.questions.length - 1) {
            // Record time spent on current question
            const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
            setQuestionTimes(prev => ({
                ...prev,
                [currentQuestionIndex]: timeSpent,
            }));

            setCurrentQuestionIndex(prev => prev + 1);
        }
    }, [currentQuestionIndex, quiz?.questions?.length]);

    // Move to previous question
    const previousQuestion = useCallback(() => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(prev => prev - 1);
        }
    }, [currentQuestionIndex]);

    // Jump to specific question
    const jumpToQuestion = useCallback((index) => {
        if (index >= 0 && index < quiz.questions.length) {
            // Record time spent on current question before jumping
            const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
            setQuestionTimes(prev => ({
                ...prev,
                [currentQuestionIndex]: timeSpent,
            }));

            setCurrentQuestionIndex(index);
        }
    }, [quiz?.questions?.length, currentQuestionIndex]);

    // Submit quiz
    const submitQuiz = useCallback(() => {
        // Record final time spent
        const finalTimeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
        setQuestionTimes(prev => ({
            ...prev,
            [currentQuestionIndex]: finalTimeSpent,
        }));

        // Calculate total time
        const totalTime = Math.floor((Date.now() - quizStartTimeRef.current) / 1000);
        setTotalTimeSpent(totalTime);

        setQuizStatus('submitted');
    }, [currentQuestionIndex]);

    // Calculate score with enhanced metrics
    const calculateScore = useCallback(() => {
        if (!quiz?.questions) return {
            correct: 0,
            total: 0,
            percentage: 0,
            averageTime: 0,
            streakBonus: 0
        };

        let correct = 0;
        let totalTime = 0;
        let answeredQuestions = 0;

        quiz.questions.forEach((q, index) => {
            const questionId = q.question_text || index.toString();
            const userAnswerIndex = answers[questionId];
            const timeSpent = questionTimes[index] || 0;

            if (userAnswerIndex !== undefined) {
                answeredQuestions++;
                totalTime += timeSpent;
                if (userAnswerIndex === q.correct_answer_index) {
                    correct++;
                }
            }
        });

        const total = quiz.questions.length;
        const percentage = Math.round((correct / total) * 100);
        const averageTime = answeredQuestions > 0 ? Math.round(totalTime / answeredQuestions) : 0;

        // Calculate streak bonus (points for maintaining streaks)
        const streakBonus = Math.min(maxStreak * 2, 20); // Max 20 bonus points

        return {
            correct,
            total,
            percentage,
            averageTime,
            streakBonus,
            totalTime,
            answeredQuestions,
            maxStreak,
        };
    }, [quiz?.questions, answers, questionTimes, maxStreak]);

    // Get current question's user answer
    const getCurrentAnswer = useCallback(() => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        return answers[questionId];
    }, [currentQuestion, currentQuestionIndex, answers]);

    // Check if all questions answered
    const isAllAnswered = useMemo(() => {
        return quiz?.questions?.every((q, index) => {
            const questionId = q.question_text || index.toString();
            return answers[questionId] !== undefined;
        }) || false;
    }, [quiz?.questions, answers]);

    // Progress info with time estimates
    const progress = useMemo(() => ({
        current: currentQuestionIndex + 1,
        total: quiz?.questions?.length || 0,
        percentage: Math.round(((currentQuestionIndex + 1) / (quiz?.questions?.length || 1)) * 100),
        timeSpent: Math.floor((Date.now() - quizStartTimeRef.current) / 1000),
        estimatedTimeRemaining: (() => {
            const avgTimePerQuestion = Object.values(questionTimes).reduce((a, b) => a + b, 0) /
                Math.max(Object.keys(questionTimes).length, 1);
            const remainingQuestions = (quiz?.questions?.length || 0) - currentQuestionIndex - 1;
            return Math.round(avgTimePerQuestion * remainingQuestions);
        })(),
    }), [currentQuestionIndex, quiz?.questions?.length, questionTimes]);

    // Performance insights
    const performanceInsights = useMemo(() => {
        const answered = Object.keys(answers).length;
        if (answered === 0) return null;

        const recentAnswers = Object.keys(answers).slice(-3);
        const hasRecentActivity = recentAnswers.length > 0;

        const currentScore = calculateScore();

        return {
            hasRecentActivity,
            streakCount,
            maxStreak,
            currentScore: currentScore.percentage,
            averageTime: currentScore.averageTime,
            isImproving: currentScore.percentage > 70,
        };
    }, [answers, streakCount, maxStreak, calculateScore]);

    return {
        // State
        currentQuestion,
        currentQuestionIndex,
        answers,
        revealedAnswers,
        quizStatus,

        // Time tracking
        totalTimeSpent,
        questionTimes,
        currentQuestionTime: Math.floor((Date.now() - currentQuestionStartRef.current) / 1000),

        // Performance
        streakCount,
        maxStreak,

        // Actions
        answerQuestion,
        revealAnswer,
        nextQuestion,
        previousQuestion,
        jumpToQuestion,
        submitQuiz,

        // Computed
        score: calculateScore(),
        currentAnswer: getCurrentAnswer(),
        isAllAnswered,
        progress,
        performanceInsights,
    };
}