/**
 * Search Page
 * 
 * TEMPORARILY DISABLED
 * The semantic search feature is temporarily disabled and will be re-enabled in a future update.
 */

'use client';

import { PageLayout } from '@/components/layout/Layout';
import { AlertCircle, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';

export default function SearchPage() {
  const router = useRouter();

  return (
    <PageLayout>
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md border-orange-200 bg-orange-50">
          <div className="p-8 text-center">
            <div className="flex justify-center mb-4">
              <AlertCircle className="h-12 w-12 text-orange-600" />
            </div>
            <h1 className="text-2xl font-bold text-orange-900 mb-3">
              Search Temporarily Disabled
            </h1>
            <p className="text-orange-800 mb-6">
              The semantic search feature is temporarily disabled and will be re-enabled 
              in a future update. For now, you can use Ctrl+F in the PDF viewer to search 
              within documents.
            </p>
            <div className="flex flex-col gap-3">
              <Button 
                onClick={() => router.push('/')}
                className="bg-orange-600 hover:bg-orange-700"
              >
                <Home className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
              <Button 
                variant="outline"
                onClick={() => router.back()}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go Back
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </PageLayout>
  );
}