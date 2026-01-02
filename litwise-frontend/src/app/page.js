/**
 * Home Page - Dashboard and Overview
 * 
 * Provides main entry point with quick actions and recent activity.
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Suspense } from 'react';
import { 
  Upload, 
  Search, 
  FileText, 
  Brain,
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Lightbulb
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layout/Layout';
import { usePapers } from '@/lib/react-query';

export default function Home() {
  const router = useRouter();
  const { data: papers, isLoading } = usePapers();
  
  // Ensure papers is always an array with proper error handling
  const safePapers = React.useMemo(() => {
    if (isLoading) return [];
    return Array.isArray(papers) ? papers : [];
  }, [papers, isLoading]);

  // Pagination for Recent Papers
  const PAPERS_PER_PAGE = 6;
  const [visiblePapersCount, setVisiblePapersCount] = useState(PAPERS_PER_PAGE);
  
  // Slice papers to show only visible amount
  const visiblePapers = safePapers.slice(0, visiblePapersCount);
  const hasMorePapers = visiblePapersCount < safePapers.length;
  const showingMorePapers = visiblePapersCount > PAPERS_PER_PAGE;
  
  // Handlers for Show More/Less
  const handleShowMorePapers = () => {
    setVisiblePapersCount(prev => prev + PAPERS_PER_PAGE);
  };
  
  const handleShowLessPapers = () => {
    setVisiblePapersCount(PAPERS_PER_PAGE);
  };

  const features = [
    {
      icon: Upload,
      title: 'Smart Upload',
      description: 'Upload PDFs and let AI extract key insights automatically',
      action: () => router.push('/upload'),
      buttonText: 'Upload Document',
      color: 'bg-blue-500'
    },
    {
      icon: Search,
      title: 'Semantic Search',
      description: 'Find relevant content using natural language queries',
      action: () => router.push('/search'),
      buttonText: 'Search Documents',
      color: 'bg-green-500'
    },
    {
      icon: Lightbulb,
      title: 'Generate Quizzes',
      description: 'Create interactive quizzes from your documents to test understanding',
      action: () => router.push('/quiz'),
      buttonText: 'Create Quiz',
      color: 'bg-cyan-500'
    },
  ];

  const stats = [
    {
      label: 'Documents Uploaded',
      value: safePapers.length || 0,
      icon: FileText
    },
    {
      label: 'AI Insights Generated',
      value: safePapers.length * 3 || 0, // Approximate
      icon: Brain
    },
    {
      label: 'Searches Performed',
      value: '0', // Could track this
      icon: Search
    },
  ];

  return (
    <PageLayout>
      {/* Hero Section */}
      <div className="relative text-center py-16 px-4 mb-8 bg-linear-to-br from-blue-50 via-purple-50 to-pink-50 rounded-3xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-linear-to-br from-blue-200/30 to-purple-200/30 rounded-full blur-3xl -z-10"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-linear-to-tr from-pink-200/30 to-orange-200/30 rounded-full blur-3xl -z-10"></div>
        
        {/* Remove animation from initial render to avoid LCP delay - render immediately */}
        <div>
          <div className="inline-block mb-4 px-4 py-1.5 bg-primary/10 border border-primary/20 rounded-full">
            <span className="text-sm font-medium text-primary">✨ AI-Powered Research Platform</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold mb-6">
            <span className="bg-linear-to-r from-gray-900 via-gray-800 to-gray-900 bg-clip-text text-transparent">
              Welcome to{' '}
            </span>
            <span className="bg-linear-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Litwise
            </span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-700 mb-10 max-w-3xl mx-auto leading-relaxed">
            Your intelligent document companion. Upload, analyze, and uncover insights 
            from your PDFs with cutting-edge AI understanding.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              size="lg" 
              onClick={() => router.push('/upload')}
              className="text-lg px-10 py-6 bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all duration-200 font-semibold"
            >
              <Upload className="mr-2 h-5 w-5" />
              Get Started
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              onClick={() => router.push('/search')}
              className="text-lg px-10 py-6 border-2 border-gray-300 hover:border-primary hover:bg-primary/5 transition-all duration-200 font-semibold"
            >
              <Search className="mr-2 h-5 w-5" />
              Search Papers
            </Button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {stats.map((stat, index) => {
          const IconComponent = stat.icon;
          const gradients = [
            'from-blue-500 to-cyan-500',
            'from-purple-500 to-pink-500',
            'from-orange-500 to-red-500'
          ];
          
          return (
            <div
              key={stat.label}
              className="transform transition-all duration-300 hover:scale-105"
            >
              <Card className="border-2 hover:border-primary/50 hover:shadow-lg transition-all duration-200 relative overflow-hidden">
                <div className={`absolute top-0 right-0 w-32 h-32 bg-linear-to-br ${gradients[index]} opacity-10 rounded-full blur-2xl`}></div>
                <CardContent className="p-6 text-center relative">
                  <div className={`inline-flex p-3 rounded-xl bg-linear-to-br ${gradients[index]} mb-4`}>
                    <IconComponent className="h-6 w-6 text-white" />
                  </div>
                  <div className="text-4xl font-extrabold bg-linear-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent mb-2">
                    {stat.value}
                  </div>
                  <div className="text-sm font-medium text-gray-600">
                    {stat.label}
                  </div>
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>

      {/* Features */}
      <div className="mb-6">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Powerful Features</h2>
          <p className="text-gray-600">Everything you need for efficient research</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const IconComponent = feature.icon;
            const gradients = [
              { bg: 'from-blue-500 to-cyan-500', hover: 'hover:from-blue-600 hover:to-cyan-600' },
              { bg: 'from-green-500 to-emerald-500', hover: 'hover:from-green-600 hover:to-emerald-600' },
              { bg: 'from-purple-500 to-pink-500', hover: 'hover:from-purple-600 hover:to-pink-600' }
            ];
            
            return (
              <div
                key={feature.title}
                className="group transform transition-all duration-300 hover:scale-105"
              >
                <Card className="h-full border-2 hover:border-primary/50 hover:shadow-xl transition-all duration-300 relative overflow-hidden">
                  <div className={`absolute top-0 right-0 w-40 h-40 bg-linear-to-br ${gradients[index].bg} opacity-5 group-hover:opacity-10 rounded-full blur-3xl transition-opacity`}></div>
                  <CardHeader className="relative">
                    <div className={`w-14 h-14 bg-linear-to-br ${gradients[index].bg} rounded-xl flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                      <IconComponent className="h-7 w-7 text-white" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col relative">
                    <p className="text-gray-600 mb-6 flex-1 leading-relaxed">
                      {feature.description}
                    </p>
                    <Button 
                      onClick={feature.action}
                      className={`w-full bg-linear-to-r ${gradients[index].bg} ${gradients[index].hover} text-white shadow-md hover:shadow-lg transition-all group/btn`}
                    >
                      {feature.buttonText}
                      <ArrowRight className="ml-2 h-4 w-4 group-hover/btn:translate-x-1 transition-transform" />
                    </Button>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Papers - Deferred with Suspense */}
      <Suspense fallback={null}>
        {safePapers.length > 0 && (
          <div
            className="mt-12"
          >
            <Card className="border-2 shadow-md">
              <CardHeader className="bg-linear-to-br from-gray-50 to-transparent border-b">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-3 text-xl">
                    <div className="p-2 bg-linear-to-br from-blue-500 to-purple-500 rounded-lg">
                      <BookOpen className="h-5 w-5 text-white" />
                    </div>
                    Recent Papers
                  </CardTitle>
                  <span className="text-sm font-medium text-primary bg-primary/10 px-3 py-1 rounded-full">
                    {Math.min(visiblePapersCount, safePapers.length)} of {safePapers.length}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Paper List - shows only visiblePapers */}
                  {visiblePapers.map((paper, idx) => (
                    <div
                      key={paper.id}
                      className="group flex items-center justify-between p-4 border-2 border-gray-200 rounded-xl hover:border-primary hover:shadow-md hover:bg-primary/5 transition-all duration-200 cursor-pointer"
                      onClick={() => router.push(`/papers/${paper.id}`)}
                    >
                    <div className="flex items-center gap-4">
                      <div className="p-2.5 bg-linear-to-br from-blue-500 to-cyan-500 rounded-lg group-hover:scale-110 transition-transform">
                        <FileText className="h-6 w-6 text-white" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-semibold text-gray-900 truncate group-hover:text-primary transition-colors">
                          {paper.title || paper.filename || 'Untitled'}
                        </h4>
                        <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
                          <span>
                            {paper.created_at && new Date(paper.created_at).toLocaleDateString()}
                          </span>
                          {paper.file_size && (
                            <>
                              <span>•</span>
                              <span className="font-medium">{(paper.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <ArrowRight className="h-5 w-5 text-gray-400 group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0" />
                    </div>
                  ))}
                  
                  {/* Show More / Show Less Buttons */}
                  <div className="flex items-center justify-center gap-3 pt-4">
                    {hasMorePapers && (
                      <Button
                        variant="outline"
                        onClick={handleShowMorePapers}
                        className="flex items-center gap-2 border-2 hover:border-primary hover:bg-primary/5 transition-all"
                      >
                        <ChevronDown className="h-4 w-4" />
                        Show More ({safePapers.length - visiblePapersCount} remaining)
                      </Button>
                    )}
                    
                    {showingMorePapers && (
                      <Button
                        variant="ghost"
                        onClick={handleShowLessPapers}
                        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                      >
                        <ChevronUp className="h-4 w-4" />
                        Show Less
                      </Button>
                    )}
                  </div>
                  
                  {/* View All Papers Link */}
                  <div className="pt-4 border-t">
                    <Button
                      variant="ghost"
                      onClick={() => router.push('/papers')}
                      className="w-full text-primary hover:text-primary hover:bg-primary/5 font-semibold group"
                    >
                      View All Papers in Library
                      <ArrowRight className="h-4 w-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </Suspense>

    </PageLayout>
  );
}