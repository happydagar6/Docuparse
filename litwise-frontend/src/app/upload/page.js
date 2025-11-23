/**
 * Upload Page
 * 
 * Dedicated page for uploading and processing research papers.
 */

'use client';

import { useRouter } from 'next/navigation';
import { UploadForm } from '@/components/forms/UploadForm';
import { PageLayout } from '@/components/layout/Layout';

export default function UploadPage() {
  const router = useRouter();

  const handleUploadSuccess = (result) => {
    // Redirect to paper reader or papers list
    if (result?.id) {
      router.push(`/papers/${result.id}`);
    } else {
      router.push('/papers');
    }
  };

  return (
    <PageLayout
      title="Upload Research Paper"
      description="Upload a PDF research paper to extract insights and enable semantic search."
    >
      <div className="max-w-4xl mx-auto">
        <UploadForm onUploadSuccess={handleUploadSuccess} />
      </div>
    </PageLayout>
  );
}