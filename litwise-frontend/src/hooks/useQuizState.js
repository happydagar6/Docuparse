'use client';

import { useState, useCallback, useMemo } from 'react';

/**
 * Custom hook for managing quiz-taking state
 * Handles: current question, answers, timer, etc.
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

    // Current question
    const currentQuestion = useMemo(() => {
        if (!quiz?.questions) return null;
        return quiz.questions[currentQuestionIndex] || null;
    }, [quiz?.questions, currentQuestionIndex]);

    // Answer current question
    const answerQuestion = useCallback((answerIndex) => {
        const questionId = currentQuestion?.question_text || currentQuestionIndex.toString();
        setAnswers(prev => ({
            ...prev,
            [questionId]: answerIndex,
        }));
    }, [currentQuestion, currentQuestionIndex]);

    // Reveal answer (show correct answer)
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
            setCurrentQuestionIndex(index);
        }
    }, [quiz?.questions?.length]);

    // Submit quiz
    const submitQuiz = useCallback(() => {
        setQuizStatus('submitted');
    }, []);

    // Calculate score
    const calculateScore = useCallback(() => {
        if (!quiz?.questions) return { correct: 0, total: 0, percentage: 0 };

        let correct = 0;
        quiz.questions.forEach((q, index) => {
            const questionId = q.question_text || index.toString();
            const userAnswerIndex = answers[questionId];
            if (userAnswerIndex === q.correct_answer_index) {
                correct++;
            }
        });

        const total = quiz.questions.length;
        return {
            correct,
            total,
            percentage: Math.round((correct / total) * 100),
        };
    }, [quiz?.questions, answers]);

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

    // Progress info
    const progress = useMemo(() => ({
        current: currentQuestionIndex + 1,
        total: quiz?.questions?.length || 0,
        percentage: Math.round(((currentQuestionIndex + 1) / (quiz?.questions?.length || 1)) * 100),
    }), [currentQuestionIndex, quiz?.questions?.length]);

    return {
        // State
        currentQuestion,
        currentQuestionIndex,
        answers,
        revealedAnswers,
        quizStatus,

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
    };
}