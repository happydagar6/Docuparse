"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useGetQuiz, useSubmitQuizAttempt } from "@/lib/react-query";
import { useQuizState } from "@/hooks/useQuizState";
import QuestionCard from "@/components/quiz/QuestionCard";
import QuizProgress from "@/components/quiz/QuizProgress";
import QuizSummary from "@/components/quiz/QuizSummary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, ChevronLeft, ChevronRight, Send } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

/**
 * Quiz Attempt Page
 *
 * Main component for taking a quiz
 * - Displays one question at a time
 * - Tracks user's progress and answers
 * - Handles submission and result display
 */

export default function QuizAttemptPage() {
  const params = useParams();
  const router = useRouter();
  const quizId = params.quiz_id;

  // Fetch quiz data
  const {
    data: quiz,
    isLoading: isQuizLoading,
    error: quizError,
  } = useGetQuiz(quizId);

  // Submit attempt mutation
  const submitAttemptMutation = useSubmitQuizAttempt(); // No quizId here; it's passed during mutation

  // Quiz state management
  const quizState = useQuizState(quiz);

  // Local state for answer reveal
  const [revealedAnswers, setRevealedAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Handle answer selection
  const handleSelectAnswer = (answerIndex) => {
    quizState.answerQuestion(answerIndex);
  };

  // Handle reveal answer
  const handleRevealAnswer = () => {
    const questionId =
      quizState.currentQuestion?.question_text ||
      quizState.currentQuestionIndex.toString();
    setRevealedAnswers((prev) => ({
      ...prev,
      [questionId]: true,
    }));
    quizState.revealAnswer(); // Update quiz state as well
  };

  // Navigate to next question
  const handleNextQuestion = () => {
    if (quizState.currentQuestionIndex < quiz.questions.length - 1) {
      quizState.nextQuestion();
    } else {
      // Last question, ready to submit
      toast.info(
        "You have reached the last queestion. Click to submit your quiz."
      );
    }
  };

  // Navigate to previous question
  const handlePreviousQuestion = () => {
    quizState.previousQuestion();
  };

  // Jump to specific question
  const handleJumpToQuestion = (index) => {
    quizState.jumpToQuestion(index);
  };

  // Handle quiz submission
  const handleSubmitQuiz = async () => {
    if (!quizState.isAllAnswered) {
      toast.error("Please answer all questions before submitting the quiz.");
      return;
    }
    setIsSubmitting(true); // Disable multiple submissions
    try {
      const attemptData = {
        quiz_id: quizId,
        responses: Object.entries(quizState.answers).reduce((acc, [questionText, answerIndex], index) => {
          // Convert question text keys to question indices
          acc[index] = answerIndex;
          return acc;
        }, {}),
      };

      submitAttemptMutation.mutate(
        { quizId, attempt: attemptData },
        {
          onSuccess: (data) => {
            quizState.submitQuiz();
            toast.success("Quiz submitted successfully!");
          },
          onError: (error) => {
            toast.error(`Failed to submit quiz: ${error.message}`);
          },
        }
      );
    } catch (error) {
      toast.error(`An unexpected error occurred: ${error.message}`);
    } finally {
      setIsSubmitting(false); // Re-enable submission
    }
  };

  // Loading state
  if (isQuizLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto" />
          <p className="text-gray-600 dark:text-gray-400">Loading quiz...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (quizError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="max-w-md">
          <CardContent className="p-6 text-center space-y-4">
            <p className="text-red-600 font-semibold">Error loading quiz</p>
            <p className="text-gray-600 text-sm">{quizError.message}</p>
            <Button onClick={() => router.back()} variant="outline">
              <ChevronLeft className="mr-2 h-4 w-4" />
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // If quiz is completed, show summary
  if (quizState.quizStatus === "submitted") {
    return (
      <div className="space-y-6">
        <QuizSummary
          quiz={quiz}
          answers={quizState.answers}
          onRetakeQuiz={() => {
            router.refresh(); // Refresh the page to retake
            window.location.reload();
          }}
          onBackHome={() => router.push("/quiz")}
        />
      </div>
    );
  }

  // Quiz in progress
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Main Content */}
      <div className="lg:col-span-3 space-y-6">
        {/* Quiz Header */}
        <div className="bg-linear-to-r from-blue-600 to-blue-700 text-white p-6 rounded-lg shadow-lg">
          <h1 className="text-3xl font-bold">Quiz Generator</h1>
          <p className="text-blue-100 mt-2">Challenge yourself and test your knowledge</p>
        </div>

        {/* Question Card */}
        {quizState.currentQuestion && (
          <QuestionCard
            question={quizState.currentQuestion}
            questionNumber={quizState.progress.current}
            selectedAnswer={quizState.currentAnswer}
            onSelectAnswer={handleSelectAnswer}
            isAnswerRevealed={
              revealedAnswers[quizState.currentQuestion.question_text] || false
            }
            onRevealAnswer={handleRevealAnswer}
            totalQuestions={quiz?.questions?.length || 0}
          />
        )}

        {/* Navigation Buttons */}
        <div className="flex gap-3 justify-between">
          <Button
            onClick={handlePreviousQuestion}
            disabled={quizState.currentQuestionIndex === 0}
            variant="outline"
            className="flex items-center gap-2"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>

          <div className="flex gap-2">
            {quizState.currentQuestionIndex === quiz.questions.length - 1 ? (
              <Button
                onClick={handleSubmitQuiz}
                disabled={!quizState.isAllAnswered || isSubmitting}
                className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Submit Quiz
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={handleNextQuestion}
                disabled={quizState.currentAnswer === null}
                className="bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Sidebar - Progress Tracker */}
      <div className="lg:col-span-1">
        <div className="sticky top-4">
          <QuizProgress
            currentQuestion={quizState.progress.current}
            totalQuestions={quiz?.questions?.length || 0}
            answers={quizState.answers}
            onJumpToQuestion={handleJumpToQuestion}
          />
        </div>
      </div>
    </div>
  );
}
