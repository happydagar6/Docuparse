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
    // ==========================================
    // 1. STATE VARIABLES (Trigger Re-renders)
    // ==========================================
    
    // Tracks which question the user is currently looking at (0 is the first question)
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

    // Stores the answers the user has selected. 
    // Format is a dictionary: { "Question 1 ID": 2 (index of selected option) }
    const [answers, setAnswers] = useState({});

    // Tracks which questions have their answers revealed to the user: { "Question 1 ID": true }
    const [revealedAnswers, setRevealedAnswers] = useState({});

    // Tracks the overall phase of the quiz: 'in-progress' | 'submitted' | 'reviewing'
    const [quizStatus, setQuizStatus] = useState('in-progress');

    // Time tracking states
    // When did they start the current question? (Unix timestamp in milliseconds)
    const [questionStartTime, setQuestionStartTime] = useState(Date.now());
    
    // Total seconds spent on the entire quiz
    const [totalTimeSpent, setTotalTimeSpent] = useState(0);
    
    // Stores how many seconds were spent on each specific question index: { 0: 15, 1: 10 }
    const [questionTimes, setQuestionTimes] = useState({});

    // Performance tracking states
    // How many questions have they gotten right in a row right now?
    const [streakCount, setStreakCount] = useState(0);
    
    // What was their highest streak during the entire quiz? (For bonus points)
    const [maxStreak, setMaxStreak] = useState(0);

    // ==========================================
    // 2. REFS (DO NOT Trigger Re-renders)
    // ==========================================
    // We use refs for precise time tracking because updating state every millisecond would freeze the app.
    const quizStartTimeRef = useRef(Date.now());
    const currentQuestionStartRef = useRef(Date.now());

    // ==========================================
    // 3. EFFECTS
    // ==========================================
    // Runs every time `currentQuestionIndex` changes (when the user goes to the next/prev question).
    // It resets the timers so we know exactly when they started looking at the new question.
    useEffect(() => {
        currentQuestionStartRef.current = Date.now();
        setQuestionStartTime(Date.now());
    }, [currentQuestionIndex]);

    // ==========================================
    // 4. COMPUTED STATE
    // ==========================================
    // Calculates the current question object.
    // It only recalculates if the `quiz` data or the `currentQuestionIndex` changes.
    const currentQuestion = useMemo(() => {
        if (!quiz?.questions) return null; // Safety check
        return quiz.questions[currentQuestionIndex] || null;
    }, [quiz?.questions, currentQuestionIndex]);

    // ==========================================
    // 5. ACTIONS
    // ==========================================
    
    // Called when the user clicks an answer option (A, B, C, D).
    const answerQuestion = useCallback((answerIndex) => {
        // Use the question text as a unique ID, or fallback to its index
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        
        // Calculate how many seconds they spent on this question before clicking an answer
        const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);

        // 1. Save their selected answer index
        setAnswers(prev => ({
            ...prev,
            [questionId]: answerIndex,
        }));

        // 2. Save the time they spent on this question
        setQuestionTimes(prev => ({
            ...prev,
            [currentQuestionIndex]: timeSpent,
        }));

        // 3. Check if the answer is correct to calculate Streaks
        const isCorrect = answerIndex === currentQuestion?.correct_answer_index;
        if (isCorrect) {
            // If correct, increase the current streak by 1
            setStreakCount(prev => {
                const newStreak = prev + 1;
                // Also update the maxStreak if the new streak is the highest they've achieved
                setMaxStreak(current => Math.max(current, newStreak));
                return newStreak;
            });
        } else {
            // If wrong, reset the current streak back to 0
            setStreakCount(0);
        }
    }, [currentQuestion, currentQuestionIndex]);

    // Marks a specific question as "revealed" so the UI can show the correct answer
    const revealAnswer = useCallback(() => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        setRevealedAnswers(prev => ({
            ...prev,
            [questionId]: true,
        }));
    }, [currentQuestion, currentQuestionIndex]);

    // Goes to the next question, but first records the time spent on the current one
    const nextQuestion = useCallback(() => {
        if (currentQuestionIndex < quiz.questions.length - 1) {
            const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
            setQuestionTimes(prev => ({
                ...prev,
                [currentQuestionIndex]: timeSpent,
            }));
            setCurrentQuestionIndex(prev => prev + 1);
        }
    }, [currentQuestionIndex, quiz?.questions?.length]);

    // Goes to the previous question
    const previousQuestion = useCallback(() => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(prev => prev - 1);
        }
    }, [currentQuestionIndex]);

    // Jumps to a specific question number (e.g., clicking on a pagination dot)
    const jumpToQuestion = useCallback((index) => {
        if (index >= 0 && index < quiz.questions.length) {
            const timeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
            setQuestionTimes(prev => ({
                ...prev,
                [currentQuestionIndex]: timeSpent,
            }));
            setCurrentQuestionIndex(index);
        }
    }, [quiz?.questions?.length, currentQuestionIndex]);

    // Called when the user clicks the final "Submit" button
    const submitQuiz = useCallback(() => {
        // Record final time spent on the very last question
        const finalTimeSpent = Math.floor((Date.now() - currentQuestionStartRef.current) / 1000);
        setQuestionTimes(prev => ({
            ...prev,
            [currentQuestionIndex]: finalTimeSpent,
        }));

        // Calculate the total time spent on the entire quiz from start to finish
        const totalTime = Math.floor((Date.now() - quizStartTimeRef.current) / 1000);
        setTotalTimeSpent(totalTime);

        // Change status to submitted so the UI knows to show the results screen
        setQuizStatus('submitted');
    }, [currentQuestionIndex]);

    // Calculates the final score, averages, and bonuses.
    // Memoized so we can call it without running heavy loops needlessly.
    const calculateScore = useCallback(() => {
        // Fallback if no questions exist
        if (!quiz?.questions) return {
            correct: 0, total: 0, percentage: 0, averageTime: 0, streakBonus: 0
        };

        let correct = 0;
        let totalTime = 0;
        let answeredQuestions = 0;

        // Loop through all questions to tally up the score and times
        quiz.questions.forEach((q, index) => {
            const questionId = q.question_text || index.toString();
            const userAnswerIndex = answers[questionId];
            const timeSpent = questionTimes[index] || 0;

            if (userAnswerIndex !== undefined) { // If the user actually answered it
                answeredQuestions++;
                totalTime += timeSpent;
                // Check if they got it right
                if (userAnswerIndex === q.correct_answer_index) {
                    correct++;
                }
            }
        });

        const total = quiz.questions.length;
        const percentage = Math.round((correct / total) * 100);
        const averageTime = answeredQuestions > 0 ? Math.round(totalTime / answeredQuestions) : 0;

        // Calculate streak bonus: 2 points per max streak, capped at 20 points
        const streakBonus = Math.min(maxStreak * 2, 20); 

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

    // Returns the answer the user selected for the current question
    const getCurrentAnswer = useCallback(() => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        return answers[questionId];
    }, [currentQuestion, currentQuestionIndex, answers]);

    // Checks if every single question has an answer recorded
    const isAllAnswered = useMemo(() => {
        return quiz?.questions?.every((q, index) => {
            const questionId = q.question_text || index.toString();
            return answers[questionId] !== undefined;
        }) || false;
    }, [quiz?.questions, answers]);

    // Calculates progress bar data and estimates remaining time
    const progress = useMemo(() => ({
        current: currentQuestionIndex + 1,
        total: quiz?.questions?.length || 0,
        percentage: Math.round(((currentQuestionIndex + 1) / (quiz?.questions?.length || 1)) * 100),
        timeSpent: Math.floor((Date.now() - quizStartTimeRef.current) / 1000),
        estimatedTimeRemaining: (() => {
            // Find average time per question and multiply by remaining questions
            const avgTimePerQuestion = Object.values(questionTimes).reduce((a, b) => a + b, 0) /
                Math.max(Object.keys(questionTimes).length, 1);
            const remainingQuestions = (quiz?.questions?.length || 0) - currentQuestionIndex - 1;
            return Math.round(avgTimePerQuestion * remainingQuestions);
        })(),
    }), [currentQuestionIndex, quiz?.questions?.length, questionTimes]);

    // Provides analytics for the UI (e.g., "You're on fire!")
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
            isImproving: currentScore.percentage > 70, // Arbitrary threshold to show positive feedback
        };
    }, [answers, streakCount, maxStreak, calculateScore]);

    // Return everything so the UI component can consume these states and functions
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