/**
 * Search Page
 * 
 * Dedicated page for semantic search across uploaded papers.
 */

'use client';

import { useRouter } from 'next/navigation';
import { SearchForm } from '@/components/forms/SearchForm';
import { PageLayout } from '@/components/layout/Layout';
import { Search, Sparkles, Zap } from 'lucide-react';

export default function SearchPage() {
  const router = useRouter();

  const handleResultClick = (result) => {
    // Navigate to paper reader
    if (result?.id) {
      router.push(`/papers/${result.id}`);
    }
  };

  return (
    <PageLayout>
      {/* Enhanced Header Section */}
      <div className="mb-12">
        <div className="relative bg-linear-to-br from-blue-50 via-cyan-50 to-teal-50 rounded-2xl p-8 md:p-12 border border-blue-100/50 overflow-hidden">
          {/* Glassmorphic overlay elements */}
          <div className="absolute top-0 right-0 w-72 h-72 bg-linear-to-br from-blue-200 to-cyan-200 rounded-full blur-3xl opacity-20 -z-10"></div>
          <div className="absolute bottom-0 left-0 w-52 h-52 bg-linear-to-tr from-teal-200 to-blue-200 rounded-full blur-3xl opacity-15 -z-10"></div>
          
          <div className="relative z-10">
            {/* Icon Section */}
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg mb-6">
              <Search className="h-8 w-8 text-blue-600" />
            </div>
            
            {/* Text Section */}
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-3">Semantic Search</h1>
            <p className="text-lg text-gray-700 max-w-2xl mb-8 leading-relaxed">
              Search across all your documents using natural language. Ask questions, find connections, and discover relevant content instantly.
            </p>
            
            {/* Feature Pills */}
            <div className="flex flex-wrap gap-3">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/40 backdrop-blur-md border border-white/60">
                <Sparkles className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium text-gray-700">AI-Powered</span>
              </div>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/40 backdrop-blur-md border border-white/60">
                <Zap className="h-4 w-4 text-orange-500" />
                <span className="text-sm font-medium text-gray-700">Instant Results</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search Form */}
      <div className="max-w-4xl mx-auto">
        <SearchForm onResultClick={handleResultClick} />
      </div>
    </PageLayout>
  );
}