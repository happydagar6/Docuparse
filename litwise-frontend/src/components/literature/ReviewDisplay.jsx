'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Copy, Download, BookOpen, FileText, Lightbulb, MessageSquare, CheckCircle, AlertCircle } from 'lucide-react';

export default function ReviewDisplay({ review }) {
    const [activeTab, setActiveTab] = useState('full');

    const content = typeof review.content === 'string' 
        ? JSON.parse(review.content) 
        : review.content;

    // Build full text for copy/export
    const buildFullText = () => {
        let text = `# Literature Review: ${review.topic}\n\n`;
        text += `**Style:** ${review.review_style} | **Papers:** ${review.paper_count} | **Words:** ${review.word_count}\n\n`;
        
        if (content.introduction) {
            text += `## Introduction\n\n${content.introduction}\n\n`;
        }
        if (content.methodology) {
            text += `## Methodology\n\n${content.methodology}\n\n`;
        }
        if (content.thematic_analysis) {
            text += `## Thematic Analysis\n\n`;
            content.thematic_analysis.forEach((theme, i) => {
                text += `### ${i + 1}. ${theme.theme_name}\n\n`;
                text += `${theme.description}\n\n`;
                if (theme.key_points?.length > 0) {
                    text += `**Key Points:**\n`;
                    theme.key_points.forEach(point => {
                        text += `- ${point}\n`;
                    });
                    text += '\n';
                }
                if (theme.supporting_papers?.length > 0) {
                    text += `*Supporting Papers: ${theme.supporting_papers.join(', ')}*\n\n`;
                }
            });
        }
        if (content.discussion) {
            text += `## Discussion\n\n${content.discussion}\n\n`;
        }
        if (content.conclusion) {
            text += `## Conclusion\n\n${content.conclusion}\n\n`;
        }
        if (content.references?.length > 0) {
            text += `## References\n\n`;
            content.references.forEach((ref, i) => {
                text += `${i + 1}. ${ref}\n`;
            });
            text += '\n';
        }

        if (content.source_coverage_note) {
            text += `---\n\n**Source Coverage Note:** ${content.source_coverage_note}\n`;
        }
        
        return text;
    };

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(buildFullText());
            toast.success('Copied to clipboard!');
        } catch {
            toast.error('Failed to copy');
        }
    };

    const handleDownload = () => {
        const text = buildFullText();
        const blob = new Blob([text], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `literature-review-${review.topic.slice(0, 30).replace(/\s+/g, '-')}.md`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Downloaded!');
    };

    const styleColors = {
        narrative: 'bg-blue-100 text-blue-800',
        systematic: 'bg-green-100 text-green-800',
        critical: 'bg-orange-100 text-orange-800',
    };

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div>
                        <CardTitle className="text-lg">{review.topic}</CardTitle>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <Badge className={styleColors[review.review_style]}>
                                {review.review_style}
                            </Badge>
                            <Badge variant="outline">{review.paper_count} papers</Badge>
                            <Badge variant="outline">{review.word_count} words</Badge>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleCopy}>
                            <Copy className="h-4 w-4 mr-1" />
                            Copy
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleDownload}>
                            <Download className="h-4 w-4 mr-1" />
                            Export
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="mb-4">
                        <TabsTrigger value="full">Full Review</TabsTrigger>
                        <TabsTrigger value="themes">Themes</TabsTrigger>
                        <TabsTrigger value="refs">References</TabsTrigger>
                    </TabsList>

                    <TabsContent value="full" className="space-y-6 max-h-[600px] overflow-y-auto">
                        {/* Introduction */}
                        {content.introduction && (
                            <Section title="Introduction" icon={BookOpen}>
                                <p className="text-sm leading-relaxed">{content.introduction}</p>
                            </Section>
                        )}

                        {/* Methodology */}
                        {content.methodology && (
                            <Section title="Methodology" icon={FileText}>
                                <p className="text-sm leading-relaxed">{content.methodology}</p>
                            </Section>
                        )}

                        {/* Thematic Analysis */}
                        {content.thematic_analysis?.length > 0 && (
                            <Section title="Thematic Analysis" icon={Lightbulb}>
                                <div className="space-y-4">
                                    {content.thematic_analysis.map((theme, i) => (
                                        <div key={i} className="border-l-2 border-primary/30 pl-4">
                                            <h4 className="font-medium">{theme.theme_name}</h4>
                                            <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                                                {theme.description}
                                            </p>
                                            {theme.key_points?.length > 0 && (
                                                <ul className="mt-2 space-y-1">
                                                    {theme.key_points.map((point, j) => (
                                                        <li key={j} className="text-sm flex items-start gap-2">
                                                            <CheckCircle className="h-3 w-3 mt-1 text-green-500 shrink-0" />
                                                            {point}
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </Section>
                        )}

                        {/* Discussion */}
                        {content.discussion && (
                            <Section title="Discussion" icon={MessageSquare}>
                                <p className="text-sm leading-relaxed">{content.discussion}</p>
                            </Section>
                        )}

                        {/* Conclusion */}
                        {content.conclusion && (
                            <Section title="Conclusion" icon={CheckCircle}>
                                <p className="text-sm leading-relaxed">{content.conclusion}</p>
                            </Section>
                        )}

                        {/* Source Coverage Note - Transparency about grounding */}
                        {content.source_coverage_note && (
                            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                                <div className="flex items-start gap-2">
                                    <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                                    <div>
                                        <p className="text-xs font-medium text-amber-800 dark:text-amber-200">Source Coverage</p>
                                        <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                                            {content.source_coverage_note}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="themes" className="space-y-4 max-h-[600px] overflow-y-auto">
                        {content.thematic_analysis?.map((theme, i) => (
                            <Card key={i}>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base">{theme.theme_name}</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm mb-3">{theme.description}</p>
                                    {theme.key_points?.length > 0 && (
                                        <div className="mb-3">
                                            <p className="text-xs font-medium mb-1">Key Points:</p>
                                            <ul className="space-y-1">
                                                {theme.key_points.map((point, j) => (
                                                    <li key={j} className="text-xs text-muted-foreground flex items-start gap-1">
                                                        <span>•</span> {point}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {theme.supporting_papers?.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                            {theme.supporting_papers.map((paper, j) => (
                                                <Badge key={j} variant="secondary" className="text-xs">
                                                    {paper.length > 40 ? paper.slice(0, 40) + '...' : paper}
                                                </Badge>
                                            ))}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )) || <p className="text-muted-foreground">No themes available</p>}
                    </TabsContent>

                    <TabsContent value="refs" className="max-h-[600px] overflow-y-auto">
                        {content.references?.length > 0 ? (
                            <ol className="space-y-2 list-decimal list-inside">
                                {content.references.map((ref, i) => (
                                    <li key={i} className="text-sm">{ref}</li>
                                ))}
                            </ol>
                        ) : (
                            <p className="text-muted-foreground">No references available</p>
                        )}
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}

function Section({ title, icon: Icon, children }) {
    return (
        <div>
            <h3 className="font-medium flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4" />
                {title}
            </h3>
            {children}
        </div>
    );
}