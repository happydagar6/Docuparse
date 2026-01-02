'use client';

/**
 * Research Editor Page
 * Main page for writing research papers with citation support
 */

import dynamic from 'next/dynamic';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { apiRequest } from '@/lib/api';

// Lazy load ResearchEditor component
const ResearchEditor = dynamic(
  () => import('@/components/editor/ResearchEditor'),
  { 
    loading: () => (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    ),
    ssr: false
  }
);

export default function ResearchEditorPage() {
    const router = useRouter();
    const [availablePapers, setAvailablePapers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    // Fetch user's papers
    useEffect(() => {
        async function fetchPapers() {
            try {
                const response = await apiRequest('/papers');
                
                // Backend returns array directly
                const papersArray = Array.isArray(response) ? response : response.papers || [];
                
                // Transform papers to required format
                // Metadata is stored directly in paper object (authors, publication_year, doi, journal_or_conference)
                const papers = papersArray.map(paper => ({
                    id: paper.id,
                    title: paper.title,
                    authors: Array.isArray(paper.authors) 
                        ? paper.authors.map(a => typeof a === 'string' ? a : a.name) 
                        : [],
                    year: paper.publication_year || null,
                    doi: paper.doi || null,
                    publisher: paper.journal_or_conference || null,
                    journal: paper.journal_or_conference || null,
                })) || [];

                setAvailablePapers(papers);
            } catch (error) {
                console.error('Error fetching papers:', error);
                toast.error('Failed to load your paper library');
            } finally {
                setIsLoading(false);
            }
        }

        fetchPapers();
    }, []);

    if (isLoading) {
        return (
            <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                <div className="text-center">
                    <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
                    <p className="text-gray-600 dark:text-gray-400">Loading your paper library...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <FileText className="h-6 w-6 text-blue-600" />
                        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                            Research Paper Editor
                        </h1>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                        {availablePapers.length} {availablePapers.length === 1 ? 'paper' : 'papers'} in library
                    </div>
                </div>
            </header>

            {/* Editor */}
            <main className="flex-1 overflow-hidden">
                <ResearchEditor availablePapers={availablePapers} />
            </main>
        </div>
    );
}