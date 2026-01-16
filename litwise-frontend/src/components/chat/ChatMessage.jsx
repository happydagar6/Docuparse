'use client';

import React, { memo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Bot, FileText, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { FormattedContent } from '@/components/ui/formatted-content';
import { Button } from '@/components/ui/button';
import ReasoningIndicator from './ReasoningIndicator';
import ResponseFormatter from './ResponseFormatter';

const ChatMessage = memo(({ message, onRetry, isStreaming = false }) => {
  const isUser = message.role === 'user';
  // Show reasoning indicator only when:
  // - Message is from assistant
  // - Message is pending (waiting for LLM response)
  // - Content is empty or not yet received
  const showReasoningLabel = !isUser && message.isPending && !message.content;

  return (
    <div className={`flex gap-1.5 md:gap-2.5 ${isUser ? 'justify-end' : 'justify-start'} w-full animate-in fade-in slide-in-from-bottom-2 duration-300 px-2 md:px-0`}>
      {!isUser && (
        <div className="shrink-0 mt-0.5 md:mt-1">
          <div className="h-6 w-6 md:h-8 md:w-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-sm shrink-0">
            <Bot className="h-3 w-3 md:h-4 md:w-4 text-white" />
          </div>
        </div>
      )}
      
      <div className={`flex flex-col max-w-[calc(100%-2rem)] sm:max-w-[80%] md:max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl p-2.5 md:p-4 shadow-sm transition-all overflow-hidden wrap-break-word ${
          isUser 
            ? message.isFailed
              ? 'bg-red-100 text-red-900 border-2 border-red-300'
              : 'bg-blue-600 text-white shadow-md' 
            : 'bg-slate-100 text-slate-900 border border-slate-200/50'
        }`}>
          {/* Reasoning Label - Only shown before content starts arriving */}
          {showReasoningLabel && (
            <ReasoningIndicator />
          )}

          {/* Main Content - Show only if there's content */}
          {message.content && (
            <div className="wrap-break-word leading-relaxed text-xs md:text-sm word-break">
              {isUser ? (
                <div className="whitespace-pre-wrap word-break wrap-break-word">{message.content}</div>
              ) : (
                <ResponseFormatter 
                  content={message.content}
                  className="space-y-4"
                />
              )}
            </div>
          )}
          
          {/* Failed message indicator */}
          {message.isFailed && (
            <div className="mt-2.5 pt-2.5 border-t border-red-300 flex items-center gap-2 text-xs">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span className="text-red-700 font-medium">Failed to send</span>
              {onRetry && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onRetry(message)}
                  className="h-6 px-2 text-xs hover:bg-red-200 ml-auto"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              )}
            </div>
          )}
          
          {/* Sources (only for assistant messages) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3 md:mt-4 pt-3 md:pt-4 border-t border-slate-200/50">
              <p className="text-xs font-semibold text-slate-700 mb-2 md:mb-3 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-blue-600" />
                Sources
              </p>
              <div className="space-y-1.5">
                {message.sources.map((source, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/50 hover:border-slate-300/60 transition-colors">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-semibold text-slate-700">Page {source.page}</span>
                      <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200 font-medium">
                        {(source.relevance_score * 100).toFixed(0)}%
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                      {source.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Icons for message role indicator */}
        <p className="text-xs text-slate-500 mt-1 md:mt-1.5 flex items-center gap-1">
          {message.isPending ? (
            <>
              <Loader2 className="h-2.5 w-2.5 md:h-3 md:w-3 animate-spin shrink-0" />
              <span className="font-medium text-xs">Sending...</span>
            </>
          ) : (
            <>
              {isUser ? (
                <User className="h-2.5 w-2.5 md:h-3 md:w-3 shrink-0" />
              ) : (
                <Bot className="h-2.5 w-2.5 md:h-3 md:w-3 shrink-0" />
              )}
            </>
          )}
        </p>
      </div>
      
      {isUser && (
        <div className="shrink-0 mt-0.5 md:mt-1 hidden md:flex">
          <div className="h-7 w-7 md:h-8 md:w-8 rounded-lg bg-linear-to-br from-blue-100 to-blue-200 flex items-center justify-center shadow-sm border border-blue-200 shrink-0">
            <User className="h-3.5 w-3.5 md:h-4 md:w-4 text-blue-700" />
          </div>
        </div>
      )}
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;