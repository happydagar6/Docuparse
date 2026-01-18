/**
 * Full-Page Chat View
 * 
 * Dedicated page for chat interface with mobile-optimized layout
 * Accessible via /chat route with paper_id query parameter
 */

'use client';

import React, { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { usePaper } from '@/lib/react-query';
import FullPageChat from '@/components/chat/FullPageChat';

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const paperId = searchParams?.get('paper_id');
  
  const { data: paper, isLoading, error } = usePaper(paperId);

  useEffect(() => {
    if (!paperId) {
      toast.error('No paper selected');
      router.push('/papers');
    }
  }, [paperId, router]);

  useEffect(() => {
    if (error) {
      toast.error('Failed to load paper');
      router.push('/papers');
    }
  }, [error, router]);

  const handleExitFullScreen = () => {
    router.push('/papers');
  };

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-linear-to-br from-slate-50 to-white">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
          <p className="text-sm text-slate-600">Loading chat...</p>
        </div>
      </div>
    );
  }

  if (!paper) {
    return null;
  }

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-linear-to-b from-white via-slate-50/30 to-white">
      {/* Header - Fixed at top with high z-index */}
      <div className="fixed top-0 left-0 right-0 z-50 border-b border-slate-200/60 bg-white/95 backdrop-blur-sm shadow-sm">
        <div className="w-full px-3 sm:px-4 md:px-6 py-3 sm:py-4 flex items-center gap-3 sm:gap-4">
          {/* Back button - always visible */}
          <Button
            onClick={handleExitFullScreen}
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0 hover:bg-slate-100 rounded-lg shrink-0 text-slate-900"
            title="Exit full screen"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          
          {/* Paper title */}
          <div className="flex-1 min-w-0">
            <h1 className="text-sm sm:text-base md:text-lg font-semibold text-slate-900 truncate">
              {paper.title || paper.filename}
            </h1>
            <p className="text-xs text-slate-500 hidden sm:block truncate">
              Chat with AI about this paper
            </p>
          </div>
        </div>
      </div>

      {/* Full-page chat component with top padding for fixed header */}
      <div className="flex-1 min-h-0 overflow-hidden pt-[calc(2.25rem+1.5rem)]">
        <FullPageChat paper={paper} />
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="h-screen w-screen flex items-center justify-center bg-linear-to-br from-slate-50 to-white">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  );
}
