'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getPapers } from '@/lib/api';
import { generateLiteratureReview } from '@/lib/literature-review-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { toast } from 'sonner';
import { Loader2, FileText, Sparkles } from 'lucide-react';

const REVIEW_STYLES = [
    { value: 'narrative', label: 'Narrative', description: 'Flowing story of research' },
    { value: 'systematic', label: 'Systematic', description: 'Structured and methodical' },
    { value: 'critical', label: 'Critical', description: 'Analytical and evaluative' },
];

export default function ReviewGenerator({ onReviewGenerated }) {
    const [selectedPapers, setSelectedPapers] = useState([]);
    const [topic, setTopic] = useState('');
    const [reviewStyle, setReviewStyle] = useState('narrative');
    const [wordLimit, setWordLimit] = useState(3000);

    const { data: papersData, isLoading: papersLoading } = useQuery({
        queryKey: ['papers'],
        queryFn: getPapers,
    });

    // API returns array directly, not { papers: [...] }
    const papers = Array.isArray(papersData) ? papersData : (papersData?.papers || []);

    const generateMutation = useMutation({
        mutationFn: generateLiteratureReview,
        onSuccess: (data) => {
            toast.success('Literature review generated!');
            onReviewGenerated(data);
        },
        onError: (error) => {
            toast.error(error.message || 'Failed to generate review');
        },
    });

    const handlePaperToggle = (paperId) => {
        setSelectedPapers((prev) =>
            prev.includes(paperId)
                ? prev.filter((id) => id !== paperId)
                : [...prev, paperId]
        );
    };

    const handleSelectAll = () => {
        if (selectedPapers.length === papers.length) {
            setSelectedPapers([]);
        } else {
            setSelectedPapers(papers.map((p) => p.id));
        }
    };

    const handleGenerate = () => {
        if (selectedPapers.length === 0) {
            toast.error('Please select at least one paper');
            return;
        }
        if (!topic.trim()) {
            toast.error('Please enter a topic');
            return;
        }

        generateMutation.mutate({
            paper_ids: selectedPapers,
            topic: topic.trim(),
            review_style: reviewStyle,
            word_limit: wordLimit,
        });
    };

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    Generate Review
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Topic Input */}
                <div className="space-y-2">
                    <Label htmlFor="topic">Review Topic</Label>
                    <Input
                        id="topic"
                        placeholder="e.g., Machine Learning in Healthcare"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                    />
                </div>

                {/* Review Style */}
                <div className="space-y-2">
                    <Label>Review Style</Label>
                    <Select value={reviewStyle} onValueChange={setReviewStyle}>
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {REVIEW_STYLES.map((style) => (
                                <SelectItem key={style.value} value={style.value}>
                                    <div>
                                        <span className="font-medium">{style.label}</span>
                                        <span className="text-muted-foreground ml-2 text-xs">
                                            - {style.description}
                                        </span>
                                    </div>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Word Limit */}
                <div className="space-y-2">
                    <Label>Word Limit: {wordLimit}</Label>
                    <Slider
                        value={[wordLimit]}
                        onValueChange={([value]) => setWordLimit(value)}
                        min={500}
                        max={10000}
                        step={500}
                    />
                </div>

                {/* Paper Selection */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <Label>Select Papers ({selectedPapers.length}/{papers.length})</Label>
                        <Button variant="ghost" size="sm" onClick={handleSelectAll} disabled={papers.length === 0}>
                            {selectedPapers.length === papers.length ? 'Deselect All' : 'Select All'}
                        </Button>
                    </div>
                    <div className="max-h-[200px] overflow-y-auto space-y-2 border rounded-md p-2">
                        {papersLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                <span className="ml-2 text-sm text-muted-foreground">Loading papers...</span>
                            </div>
                        ) : papers.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-4">
                                No papers uploaded yet. Upload some papers first.
                            </p>
                        ) : (
                            papers.map((paper) => (
                                <div
                                    key={paper.id}
                                    className="flex items-start gap-2 p-2 rounded hover:bg-muted/50"
                                >
                                    <Checkbox
                                        id={paper.id}
                                        checked={selectedPapers.includes(paper.id)}
                                        onCheckedChange={() => handlePaperToggle(paper.id)}
                                    />
                                    <label
                                        htmlFor={paper.id}
                                        className="text-sm cursor-pointer flex-1"
                                    >
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-3 w-3 shrink-0" />
                                            <span className="line-clamp-2">{paper.title}</span>
                                        </div>
                                    </label>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Generate Button */}
                <Button
                    className="w-full"
                    onClick={handleGenerate}
                    disabled={generateMutation.isPending || selectedPapers.length === 0 || !topic.trim()}
                >
                    {generateMutation.isPending ? (
                        <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Generating... (30-60s)
                        </>
                    ) : (
                        <>
                            <Sparkles className="h-4 w-4 mr-2" />
                            Generate Literature Review
                        </>
                    )}
                </Button>
            </CardContent>
        </Card>
    );
}

