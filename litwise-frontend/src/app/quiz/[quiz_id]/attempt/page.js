"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useGetQuiz, useSubmitQuizAttempt } from "@/lib/react-query";
import { useQuizState } from "@/hooks/useQuizState";
import QuestionCard from "@/components/quiz/QuestionCard";
import QuizProgress from "@/components/quiz/QuizProgress";
import QuizSummary from "@/components/quiz/QuizSummary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, ChevronLeft, ChevronRight, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Target } from "lucide-react";
import { BookOpen } from "lucide-react";
import { Clock } from "lucide-react";
import { AlertCircle } from "lucide-react";

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
    <div className="min-h-screen bg-linear-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-blue-900/20">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Main Content Area */}
          <div className="lg:col-span-3 space-y-8">
            {/* Enhanced Quiz Header */}
            <div className="relative overflow-hidden bg-linear-to-r from-blue-600 via-purple-600 to-indigo-700 text-white rounded-2xl shadow-2xl">
              {/* Background decoration */}
              <div className="absolute inset-0 bg-black/10" />
              <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/5 rounded-full blur-3xl" />
              <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl" />

              <div className="relative p-8">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
                        <Sparkles className="w-8 h-8" />
                      </div>
                      <div>
                        <h1 className="text-3xl font-bold">Quiz Challenge</h1>
                        <p className="text-blue-100 text-lg">Test your knowledge and skills</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-blue-100">
                      <span className="flex items-center gap-1">
                        <Target className="w-4 h-4" />
                        {quiz?.title || 'Quiz'}
                      </span>
                      <span className="flex items-center gap-1">
                        <BookOpen className="w-4 h-4" />
                        {quiz?.questions?.length || 0} Questions
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {quizState.progress.percentage}% Complete
                      </span>
                    </div>
                  </div>

                  {/* Progress indicator */}
                  <div className="hidden md:flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-2xl font-bold">
                        {quizState.progress.current}/{quiz?.questions?.length || 0}
                      </div>
                      <div className="text-sm text-blue-100">Questions</div>
                    </div>
                    <div className="w-16 h-16 relative">
                      <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="rgba(255,255,255,0.2)"
                          strokeWidth="2"
                        />
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="white"
                          strokeWidth="2"
                          strokeDasharray={`${quizState.progress.percentage}, 100`}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center text-sm font-bold">
                        {quizState.progress.percentage}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Question Card with enhanced animations */}
            <div>
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
            </div>

            {/* Enhanced Navigation Section */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg border-0 p-6">
              <div className="flex items-center justify-between">
                {/* Previous Button */}
                <Button
                  onClick={handlePreviousQuestion}
                  disabled={quizState.currentQuestionIndex === 0}
                  variant="outline"
                  size="lg"
                  className={cn(
                    'flex items-center gap-3 px-6 py-3 transition-all duration-300',
                    quizState.currentQuestionIndex === 0
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:shadow-md'
                  )}
                >
                  <ChevronLeft className="w-5 h-5" />
                  <span className="hidden sm:inline">Previous</span>
                </Button>

                {/* Progress indicator for mobile */}
                <div className="md:hidden flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <span>{quizState.progress.current} of {quiz?.questions?.length || 0}</span>
                </div>

                {/* Next/Submit Button */}
                <div className="flex gap-3">
                  {quizState.currentQuestionIndex === quiz.questions.length - 1 ? (
                    <div>
                      <Button
                        onClick={handleSubmitQuiz}
                        disabled={!quizState.isAllAnswered || isSubmitting}
                        size="lg"
                        className={cn(
                          'flex items-center gap-3 px-8 py-3 bg-linear-to-r transition-all duration-300 shadow-lg',
                          !quizState.isAllAnswered || isSubmitting
                            ? 'from-gray-400 to-gray-500 cursor-not-allowed'
                            : 'from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 hover:shadow-xl'
                        )}
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span className="hidden sm:inline">Submitting...</span>
                          </>
                        ) : (
                          <>
                            <Send className="w-5 h-5" />
                            <span className="hidden sm:inline">Submit Quiz</span>
                          </>
                        )}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      onClick={handleNextQuestion}
                      disabled={quizState.currentAnswer === null}
                      size="lg"
                      className={cn(
                        'flex items-center gap-3 px-8 py-3 bg-linear-to-r transition-all duration-300 shadow-lg',
                        quizState.currentAnswer === null
                          ? 'from-gray-400 to-gray-500 cursor-not-allowed'
                          : 'from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:shadow-xl'
                      )}
                    >
                      <span className="hidden sm:inline">Next</span>
                      <ChevronRight className="w-5 h-5" />
                    </Button>
                  )}
                </div>
              </div>

              {/* Progress hint */}
              {!quizState.isAllAnswered && quizState.currentQuestionIndex === quiz.questions.length - 1 && (
                <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-200">
                    <AlertCircle className="w-5 h-5" />
                    <span className="text-sm font-medium">
                      Complete all questions to submit your quiz
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Enhanced Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-8">
              <QuizProgress
                currentQuestion={quizState.progress.current}
                totalQuestions={quiz?.questions?.length || 0}
                answers={quizState.answers}
                onJumpToQuestion={handleJumpToQuestion}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
