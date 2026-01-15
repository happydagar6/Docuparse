"use client";

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import dynamic from 'next/dynamic';
import { deleteLiteratureReview, getLiteratureReviews } from '@/lib/literature-review-api';
import { toast } from 'sonner';
import { PageLayout } from '../../components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Clock, Trash2, BookOpen, Loader2 } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../../components/ui/alert-dialog';
import { formatDistanceToNow } from 'date-fns';

// Lazy load heavy components
const ReviewGenerator = dynamic(() => import('../../components/literature/literature-review'), {
  loading: () => <div className="flex justify-center p-8"><Loader2 className="animate-spin h-8 w-8 text-blue-500" /></div>
});
const ReviewDisplay = dynamic(() => import('../../components/literature/ReviewDisplay'), {
  loading: () => <div className="flex justify-center p-8"><Loader2 className="animate-spin h-8 w-8 text-blue-500" /></div>
});

export default function LiteratureReviewPage() {
    const [currentReview, setCurrentReview] = useState(null);
    const [selectedReviewId, setSelectedReviewId] = useState(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [reviewToDelete, setReviewToDelete] = useState(null);

    const queryClient = useQueryClient();

    const { data, refetch, isLoading, isError, error } = useQuery({
        queryKey: ['literature-reviews'],
        queryFn: getLiteratureReviews,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteLiteratureReview,
        onSuccess: () => {
            toast.success("Literature review deleted successfully");
            queryClient.invalidateQueries({ queryKey: ['literature-reviews'] });
            if (selectedReviewId === reviewToDelete?.id) {
                setSelectedReviewId(null);
                setCurrentReview(null);
            }
            setDeleteDialogOpen(false);
            setReviewToDelete(null);
        },
        onError: () => {
            toast.error("Failed to delete literature review");
        },
    });

    const reviews = data?.reviews || []; // Ensure reviews is always an array

    const handleReviewGenerated = (review) => {
        setCurrentReview(review);
        setSelectedReviewId(review.id);
        refetch(); // Refresh the list of reviews
    };

    const handleSelectReview = (review) => {
        setCurrentReview(review);
        setSelectedReviewId(review.id);
    };

    const handleDeleteClick = (e, review) => {
        e.stopPropagation();
        setReviewToDelete(review);
        setDeleteDialogOpen(true);
    };

    const styleColors = {
        narrative: 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 border-blue-200',
        systematic: 'bg-gradient-to-r from-green-50 to-green-100 text-green-700 border-green-200',
        critical: 'bg-gradient-to-r from-purple-50 to-purple-100 text-purple-700 border-purple-200',
    };

    return (
        <PageLayout>
        {/* Enhanced Header Section */}
        <div className="mb-8">
          <div className="relative bg-linear-to-br from-green-50 via-emerald-50 to-teal-50 rounded-2xl p-8 md:p-10 border border-green-100/50 overflow-hidden">
            {/* Glassmorphic background elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-linear-to-br from-green-200 to-emerald-200 rounded-full blur-3xl opacity-20 -z-10"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-linear-to-tr from-emerald-200 to-teal-200 rounded-full blur-3xl opacity-15 -z-10"></div>
            
            <div className="relative z-10 flex items-start gap-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg">
                <BookOpen className="h-7 w-7 text-green-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">Literature Reviews</h1>
                <p className="text-gray-700 leading-relaxed">Generate comprehensive, well-structured literature reviews from your document collection with AI-powered synthesis.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Page content goes here */}

        <div className='grid grid-cols-1 lg:grid-cols-3 gap-6 p-6'>
            {/* Generator Panel */}
            <div className='lg:col-span-1 space-y-5'>
                <ReviewGenerator onReviewGenerated={handleReviewGenerated} />

                    {/* History */}
                    <Card className="border-2 shadow-sm hover:shadow-md transition-shadow">
                        <CardHeader className="pb-3 bg-linear-to-br from-gray-50 to-transparent">
                            <CardTitle className="text-base flex items-center gap-2">
                                <div className="p-1.5 bg-blue-100 rounded-lg">
                                    <Clock className="h-4 w-4 text-blue-600" />
                                </div>
                                Recent Reviews
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 max-h-[450px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
                            {isLoading ? (
                                <div className="flex items-center justify-center py-4">
                                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                    <span className="ml-2 text-sm text-muted-foreground">Loading reviews...</span>
                                </div>
                            ) : isError ? (
                                <p className='text-sm text-red-500'>Error loading reviews: {error?.message}</p>
                            ) : reviews.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                    <div className="p-3 bg-gray-100 rounded-full mb-3">
                                        <BookOpen className="h-6 w-6 text-gray-400" />
                                    </div>
                                    <p className='text-sm text-muted-foreground'>No reviews generated yet</p>
                                    <p className='text-xs text-muted-foreground mt-1'>Generate your first review to get started</p>
                                </div>
                            ) : (
                                reviews.map((review) => (
                                    <div
                                        key={review.id}
                                        onClick={() => handleSelectReview(review)}
                                        className={`group p-3 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                                            selectedReviewId === review.id 
                                                ? 'border-primary bg-primary/5 shadow-sm' 
                                                : 'border-gray-200 hover:border-primary/50 hover:shadow-sm hover:bg-gray-50'
                                        }`}
                                    >
                                        <div className="flex justify-between items-start gap-2">
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium text-sm truncate">{review.topic}</p>
                                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                    <Badge variant="secondary" className={`text-xs border ${styleColors[review.review_style]}`}>
                                                        {review.review_style}
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        {review.paper_count} papers
                                                    </span>
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-1">
                                                    {formatDistanceToNow(new Date(review.created_at), { addSuffix: true })}
                                                </p>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 shrink-0 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity hover:bg-red-50 hover:text-red-600"
                                                onClick={(e) => handleDeleteClick(e, review)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Display Panel */}
                <div className="lg:col-span-2">
                    {currentReview ? (
                        <ReviewDisplay review={currentReview} />
                    ) : (
                        <Card className="h-full min-h-[600px] flex items-center justify-center border-2 border-dashed border-gray-300 bg-linear-to-br from-gray-50 to-transparent">
                            <div className="text-center space-y-4 p-8">
                                <div className="p-4 bg-linear-to-br from-blue-50 to-purple-50 rounded-2xl inline-block">
                                    <BookOpen className="h-12 w-12 mx-auto text-blue-600" />
                                </div>
                                <div>
                                    <p className="text-lg font-medium text-gray-700 mb-2">
                                        No Review Selected
                                    </p>
                                    <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                                        Select papers from the panel, enter your topic, and generate a comprehensive literature review
                                    </p>
                                </div>
                            </div>
                        </Card>
                    )}
                </div>
            </div>

            {/* Delete Dialog */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Literature Review?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete this literature review. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate(reviewToDelete?.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleteMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                'Delete'
                            )}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </PageLayout>
    );
}