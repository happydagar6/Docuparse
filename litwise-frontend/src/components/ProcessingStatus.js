"use client";

import React from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Spinner } from './ui/spinner';
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  Loader2,
  Sparkles,
  AlertCircle 
} from 'lucide-react';
import { toast } from 'sonner';
import { useProcessPaper } from '../lib/react-query';

const statusConfig = {
  uploaded: {
    label: 'Ready to Process',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: Clock,
    description: 'PDF uploaded, ready for AI processing'
  },
  processing: {
    label: 'Processing...',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: Loader2,
    description: 'AI is analyzing the document'
  },
  completed: {
    label: 'Processed',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: CheckCircle,
    description: 'AI summary generated successfully'
  },
  failed: {
    label: 'Failed',
    color: 'bg-red-100 text-red-800 border-red-200',
    icon: XCircle,
    description: 'Processing failed, try again'
  }
};

export function ProcessingStatus({ 
  paper, 
  showButton = true, 
  size = 'default',
  className = '' 
}) {
  const processPaper = useProcessPaper();
  const status = paper?.processing_status || 'uploaded';
  const config = statusConfig[status];
  const Icon = config.icon;

  const handleProcess = async () => {
    if (paper?.id) {
      try {
        toast.promise(
          processPaper.mutateAsync(paper.id),
          {
            loading: 'Generating AI summary...',
            success: 'AI summary generated successfully!',
            error: (error) => `Failed to generate summary: ${error.message || 'Unknown error'}`
          }
        );
      } catch (error) {
        // Error is handled by toast.promise
        console.error('Processing failed:', error);
      }
    }
  };

  const isProcessing = status === 'processing' || processPaper.isPending;
  const canProcess = status === 'uploaded' || status === 'failed';

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Badge 
        variant="outline" 
        className={`${config.color} flex items-center gap-1 ${
          size === 'sm' ? 'text-xs px-2 py-1' : 'px-3 py-1'
        }`}
      >
        <Icon 
          className={`h-3 w-3 ${isProcessing ? 'animate-spin' : ''}`} 
        />
        {config.label}
      </Badge>

      {showButton && canProcess && (
        <Button
          onClick={handleProcess}
          disabled={isProcessing}
          size={size === 'sm' ? 'sm' : 'default'}
          variant={status === 'failed' ? 'outline' : 'default'}
          className="flex items-center gap-1"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              {status === 'failed' ? 'Retry AI Summary' : 'Generate AI Summary'}
            </>
          )}
        </Button>
      )}

      {paper?.processing_error && status === 'failed' && (
        <div className="flex items-center gap-1 text-red-600 text-sm">
          <AlertCircle className="h-4 w-4" />
          <span className="truncate max-w-xs" title={paper.processing_error}>
            Error: {paper.processing_error}
          </span>
        </div>
      )}
    </div>
  );
}

// Compact version for paper cards
export function ProcessingBadge({ paper, className = '' }) {
  return (
    <ProcessingStatus 
      paper={paper} 
      showButton={false}
      size="sm"
      className={className}
    />
  );
}