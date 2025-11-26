/**
 * Home Page - Dashboard and Overview
 * 
 * Provides main entry point with quick actions and recent activity.
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Upload, 
  Search, 
  FileText, 
  Brain, 
  Zap,
  ArrowRight,
  BookOpen 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layout/Layout';
import EnhancedFooter from '@/components/layout/EnhancedFooter';
import { usePapers } from '@/lib/react-query';

export default function Home() {
  const router = useRouter();
  const { data: papers, isLoading } = usePapers();
  
  // Ensure papers is always an array with proper error handling
  const safePapers = React.useMemo(() => {
    if (isLoading) return [];
    return Array.isArray(papers) ? papers : [];
  }, [papers, isLoading]);

  const features = [
    {
      icon: Upload,
      title: 'Smart Upload',
      description: 'Upload PDFs and let AI extract key insights automatically',
      action: () => router.push('/upload'),
      buttonText: 'Upload Paper',
      color: 'bg-blue-500'
    },
    {
      icon: Search,
      title: 'Semantic Search',
      description: 'Find relevant papers using natural language queries',
      action: () => router.push('/search'),
      buttonText: 'Search Papers',
      color: 'bg-green-500'
    },
    {
      icon: FileText,
      title: 'Paper Library',
      description: 'Browse and manage your collection of research papers',
      action: () => router.push('/papers'),
      buttonText: 'View Library',
      color: 'bg-purple-500'
    },
  ];

  const stats = [
    {
      label: 'Papers Uploaded',
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
      <div className="text-center py-12 px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Welcome to{' '}
            <span className="text-primary">Litwise</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Your AI-powered research companion. Upload, analyze, and discover insights 
            from research papers with advanced semantic understanding.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              size="lg" 
              onClick={() => router.push('/upload')}
              className="text-lg px-8 py-3"
            >
              <Upload className="mr-2 h-5 w-5" />
              Get Started
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              onClick={() => router.push('/search')}
              className="text-lg px-8 py-3"
            >
              <Search className="mr-2 h-5 w-5" />
              Search Papers
            </Button>
          </div>
        </motion.div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {stats.map((stat, index) => {
          const IconComponent = stat.icon;
          
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 + 0.2 }}
            >
              <Card>
                <CardContent className="p-6 text-center">
                  <IconComponent className="h-8 w-8 mx-auto mb-3 text-primary" />
                  <div className="text-3xl font-bold text-gray-900 mb-1">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-600">
                    {stat.label}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        {features.map((feature, index) => {
          const IconComponent = feature.icon;
          
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 + 0.4 }}
            >
              <Card className="h-full hover:shadow-lg transition-shadow duration-300">
                <CardHeader>
                  <div className={`w-12 h-12 ${feature.color} rounded-lg flex items-center justify-center mb-4`}>
                    <IconComponent className="h-6 w-6 text-white" />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <p className="text-gray-600 mb-6 flex-1">
                    {feature.description}
                  </p>
                  <Button 
                    onClick={feature.action}
                    className="w-full"
                  >
                    {feature.buttonText}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Recent Papers */}
      {safePapers.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Recent Papers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {safePapers.slice(0, 3).map((paper, index) => (
                  <div
                    key={paper.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-primary transition-colors cursor-pointer"
                    onClick={() => router.push(`/papers/${paper.id}`)}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-8 w-8 text-blue-500" />
                      <div>
                        <h4 className="font-medium">
                          {paper.title || paper.filename || 'Untitled'}
                        </h4>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <span>
                            {paper.created_at && new Date(paper.created_at).toLocaleDateString()}
                          </span>
                          {paper.file_size && (
                            <>
                              <span>•</span>
                              <span>{(paper.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-gray-400" />
                  </div>
                ))}
                
                {safePapers.length > 3 && (
                  <Button
                    variant="ghost"
                    onClick={() => router.push('/papers')}
                    className="w-full"
                  >
                    View All Papers ({safePapers.length})
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Enhanced Footer */}
      <EnhancedFooter />
    </PageLayout>
  );
}