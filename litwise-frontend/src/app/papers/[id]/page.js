/**
 * Paper Detail Page
 * 
 * Displays individual paper with AI insights and interactive reader.
 */

'use client';

import { useParams, useRouter } from 'next/navigation';
import { PaperReader } from '@/components/reader/PaperReader';
import { usePaper } from '@/lib/react-query';

export default function PaperPage() {
  const params = useParams();
  const router = useRouter();
  const paperId = params.id;
  
  const { data: paper, isLoading, error } = usePaper(paperId);

  const handleBack = () => {
    router.back();
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading paper...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Paper not found
          </h2>
          <p className="text-gray-600 mb-4">
            The paper you&apos;re looking for doesn&apos;t exist or has been removed.
          </p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <p>No paper data available</p>
        </div>
      </div>
    );
  }

  return <PaperReader paper={paper} onBack={handleBack} />;
}