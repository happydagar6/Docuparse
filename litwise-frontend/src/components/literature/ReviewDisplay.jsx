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
        narrative: 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 border-blue-200',
        systematic: 'bg-gradient-to-r from-green-50 to-green-100 text-green-700 border-green-200',
        critical: 'bg-gradient-to-r from-orange-50 to-orange-100 text-orange-700 border-orange-200',
    };

    return (
        <Card className="border-2 shadow-md">
            <CardHeader className="pb-4 bg-gradient-to-br from-gray-50 to-transparent border-b">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div className="flex-1">
                        <CardTitle className="text-xl font-bold mb-2">{review.topic}</CardTitle>
                        <div className="flex items-center gap-2 flex-wrap">
                            <Badge className={`${styleColors[review.review_style]} border font-medium`}>
                                {review.review_style}
                            </Badge>
                            <Badge variant="outline" className="bg-white">
                                {review.paper_count} {review.paper_count === 1 ? 'paper' : 'papers'}
                            </Badge>
                            <Badge variant="outline" className="bg-white">
                                {review.word_count.toLocaleString()} words
                            </Badge>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={handleCopy}
                            className="hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300 transition-colors"
                        >
                            <Copy className="h-4 w-4 mr-1.5" />
                            Copy
                        </Button>
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={handleDownload}
                            className="hover:bg-green-50 hover:text-green-600 hover:border-green-300 transition-colors"
                        >
                            <Download className="h-4 w-4 mr-1.5" />
                            Export
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="mb-5 grid w-full grid-cols-3 h-11">
                        <TabsTrigger value="full" className="data-[state=active]:bg-primary data-[state=active]:text-white">
                            Full Review
                        </TabsTrigger>
                        <TabsTrigger value="themes" className="data-[state=active]:bg-primary data-[state=active]:text-white">
                            Themes
                        </TabsTrigger>
                        <TabsTrigger value="refs" className="data-[state=active]:bg-primary data-[state=active]:text-white">
                            References
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="full" className="space-y-6 max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent pr-2">
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
                                <div className="space-y-5">
                                    {content.thematic_analysis.map((theme, i) => (
                                        <div key={i} className="border-l-4 border-primary/40 pl-4 py-2 bg-gradient-to-r from-primary/5 to-transparent rounded-r-lg">
                                            <h4 className="font-semibold text-base mb-2 text-gray-800">{theme.theme_name}</h4>
                                            <p className="text-sm text-gray-600 leading-relaxed mb-3">
                                                {theme.description}
                                            </p>
                                            {theme.key_points?.length > 0 && (
                                                <ul className="space-y-2">
                                                    {theme.key_points.map((point, j) => (
                                                        <li key={j} className="text-sm flex items-start gap-2.5">
                                                            <div className="mt-0.5">
                                                                <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                                                            </div>
                                                            <span className="flex-1">{point}</span>
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
                            <div className="mt-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-200 rounded-xl">
                                <div className="flex items-start gap-3">
                                    <div className="p-1.5 bg-amber-100 rounded-lg">
                                        <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-semibold text-amber-900 mb-1">Source Coverage Note</p>
                                        <p className="text-sm text-amber-800 leading-relaxed">
                                            {content.source_coverage_note}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="themes" className="space-y-4 max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent pr-2">
                        {content.thematic_analysis?.map((theme, i) => (
                            <Card key={i} className="border-2 hover:shadow-md transition-shadow">
                                <CardHeader className="pb-3 bg-gradient-to-br from-primary/5 to-transparent">
                                    <CardTitle className="text-base flex items-start gap-2">
                                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                                            {i + 1}
                                        </span>
                                        {theme.theme_name}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm mb-4 leading-relaxed text-gray-700">{theme.description}</p>
                                    {theme.key_points?.length > 0 && (
                                        <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-200">
                                            <p className="text-xs font-semibold text-green-900 mb-2">Key Points:</p>
                                            <ul className="space-y-1.5">
                                                {theme.key_points.map((point, j) => (
                                                    <li key={j} className="text-xs text-green-800 flex items-start gap-2">
                                                        <CheckCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                                                        <span>{point}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {theme.supporting_papers?.length > 0 && (
                                        <div>
                                            <p className="text-xs font-medium text-gray-600 mb-2">Supporting Papers:</p>
                                            <div className="flex flex-wrap gap-1.5">
                                                {theme.supporting_papers.map((paper, j) => (
                                                    <Badge key={j} variant="secondary" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                                                        {paper.length > 40 ? paper.slice(0, 40) + '...' : paper}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )) || (
                            <div className="flex flex-col items-center justify-center py-12">
                                <div className="p-3 bg-gray-100 rounded-full mb-3">
                                    <Lightbulb className="h-6 w-6 text-gray-400" />
                                </div>
                                <p className="text-muted-foreground">No themes available</p>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="refs" className="max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent pr-2">
                        {content.references?.length > 0 ? (
                            <ol className="space-y-3 list-none">
                                {content.references.map((ref, i) => (
                                    <li key={i} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors">
                                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary shrink-0">
                                            {i + 1}
                                        </span>
                                        <span className="text-sm flex-1 leading-relaxed">{ref}</span>
                                    </li>
                                ))}
                            </ol>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12">
                                <div className="p-3 bg-gray-100 rounded-full mb-3">
                                    <FileText className="h-6 w-6 text-gray-400" />
                                </div>
                                <p className="text-muted-foreground">No references available</p>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}

function Section({ title, icon: Icon, children }) {
    return (
        <div className="pb-4 border-b border-gray-100 last:border-0">
            <h3 className="font-semibold text-base flex items-center gap-2.5 mb-3 text-gray-800">
                <div className="p-1.5 bg-primary/10 rounded-lg">
                    <Icon className="h-4 w-4 text-primary" />
                </div>
                {title}
            </h3>
            <div className="text-gray-700">
                {children}
            </div>
        </div>
    );
}