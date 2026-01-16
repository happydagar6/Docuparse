/**
 * Full-Page Chat View
 * 
 * Dedicated page for chat interface with mobile-optimized layout
 * Accessible via /chat route with paper_id query parameter
 */

'use client';

import React, { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';
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

  const handleBack = () => {
    if (paperId) {
      router.push(`/papers/${paperId}`);
    } else {
      router.back();
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-white">
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
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gradient-to-b from-white via-slate-50/30 to-white">
      {/* Header - Fixed at top */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex-shrink-0 border-b border-slate-200/60 bg-white/95 backdrop-blur-sm shadow-sm z-10"
      >
        <div className="container mx-auto px-3 sm:px-4 md:px-6 py-3 sm:py-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <Button
              onClick={handleBack}
              variant="ghost"
              size="sm"
              className="hover:bg-slate-100 rounded-lg h-9 px-3"
            >
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              <span className="hidden sm:inline">Back</span>
            </Button>
            
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
      </motion.div>

      {/* Full-page chat component */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="flex-1 min-h-0 overflow-hidden"
      >
        <FullPageChat paper={paper} />
      </motion.div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="h-screen w-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-white">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  );
}
