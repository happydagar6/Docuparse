"use client";

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { deleteLiteratureReview, getLiteratureReviews } from '@/lib/literature-review-api';
import { toast } from 'sonner';
import { PageLayout } from '../../components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Clock, Trash2, BookOpen, Loader2 } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../../components/ui/alert-dialog';
import ReviewGenerator from '../../components/literature/literature-review';
import ReviewDisplay from '../../components/literature/ReviewDisplay';
import { formatDistanceToNow } from 'date-fns';

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
        narrative: 'bg-blue-100 text-blue-800',
        systematic: 'bg-green-100 text-green-800',
        critical: 'bg-purple-100 text-purple-800',
    };

    return (
        <PageLayout
        title="Literature Reviews Generator"
        description="Generate comprehensive literature reviews tailored to your research needs."
      >
        {/* Page content goes here */}

        <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
            {/* Generator Panel */}
            <div className='lg:col-span-1 space-y-4'>
                <ReviewGenerator onReviewGenerated={handleReviewGenerated} />

                    {/* History */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Clock className="h-4 w-4" />
                                Recent Reviews
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
                            {isLoading ? (
                                <div className="flex items-center justify-center py-4">
                                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                    <span className="ml-2 text-sm text-muted-foreground">Loading reviews...</span>
                                </div>
                            ) : isError ? (
                                <p className='text-sm text-red-500'>Error loading reviews: {error?.message}</p>
                            ) : reviews.length === 0 ? (
                                <p className='text-sm text-muted-foreground'>No reviews generated yet.</p>
                            ) : (
                                reviews.map((review) => (
                                    <div
                                        key={review.id}
                                        onClick={() => handleSelectReview(review)}
                                        className={`p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors ${
                                            selectedReviewId === review.id ? 'border-primary bg-muted/30' : ''
                                        }`}
                                    >
                                        <div className="flex justify-between items-start gap-2">
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium text-sm truncate">{review.topic}</p>
                                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                    <Badge variant="secondary" className={`text-xs ${styleColors[review.review_style]}`}>
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
                                                className="h-8 w-8 shrink-0"
                                                onClick={(e) => handleDeleteClick(e, review)}
                                            >
                                                <Trash2 className="h-4 w-4 text-destructive" />
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
                        <Card className="h-full min-h-[500px] flex items-center justify-center">
                            <div className="text-center space-y-3">
                                <BookOpen className="h-12 w-12 mx-auto text-muted-foreground" />
                                <p className="text-muted-foreground">
                                    Select papers and generate a literature review
                                </p>
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