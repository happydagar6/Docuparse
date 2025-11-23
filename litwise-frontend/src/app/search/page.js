/**
 * Search Page
 * 
 * Dedicated page for semantic search across uploaded papers.
 */

'use client';

import { useRouter } from 'next/navigation';
import { SearchForm } from '@/components/forms/SearchForm';
import { PageLayout } from '@/components/layout/Layout';

export default function SearchPage() {
  const router = useRouter();

  const handleResultClick = (result) => {
    // Navigate to paper reader
    if (result?.id) {
      router.push(`/papers/${result.id}`);
    }
  };

  return (
    <PageLayout
      title="Semantic Search"
      description="Find relevant research papers using natural language queries."
    >
      <SearchForm onResultClick={handleResultClick} />
    </PageLayout>
  );
}