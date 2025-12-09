'use client';

import React, { memo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Bot, FileText, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns';
import { FormattedContent } from '@/components/ui/formatted-content';
import { Button } from '@/components/ui/button';

const ChatMessage = memo(({ message, onRetry }) => {
  const isUser = message.role === 'user';
  
  // Handle both timestamp and created_at fields with error handling
  let timestamp;
  try {
    const dateValue = message.created_at || message.timestamp;
    if (!dateValue) {
      timestamp = new Date(); // Fallback to current time
    } else {
      timestamp = new Date(dateValue);
      // Check if the date is valid
      if (isNaN(timestamp.getTime())) {
        timestamp = new Date(); // Fallback to current time
      }
    }
  } catch (error) {
    console.warn('Invalid date in message:', error);
    timestamp = new Date(); // Fallback to current time
  }

  // Format time intelligently
  const formatMessageTime = (date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffInMinutes < 1) {
      return 'Just now';
    } else if (diffInMinutes < 60) {
      return `${diffInMinutes}m ago`;
    } else if (isToday(date)) {
      return format(date, 'h:mm a');
    } else if (isYesterday(date)) {
      return `Yesterday, ${format(date, 'h:mm a')}`;
    } else {
      return format(date, 'MMM d, h:mm a');
    }
  };

  return (
    <div className={`flex gap-2 md:gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      {!isUser && (
        <div className="shrink-0 mt-1">
          <div className="h-8 w-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-sm">
            <Bot className="h-4 w-4 text-white" />
          </div>
        </div>
      )}
      
      <div className={`flex-1 max-w-[85%] md:max-w-[70%] ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`rounded-2xl p-3 md:p-4 shadow-sm transition-all ${
          isUser 
            ? message.isFailed
              ? 'bg-red-100 text-red-900 border-2 border-red-300 ml-auto'
              : 'bg-blue-600 text-white ml-auto shadow-md' 
            : 'bg-slate-100 text-slate-900 border border-slate-200/50'
        }`}>
          <div className="wrap-break-word leading-relaxed">
            {isUser ? (
              <div className="whitespace-pre-wrap wrap-break-word">{message.content}</div>
            ) : (
              <FormattedContent content={message.content} />
            )}
          </div>
          
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
        
        {/* Timestamp with pending state */}
        <p className="text-xs text-slate-500 mt-1.5 md:mt-2 flex items-center gap-1.5">
          {message.isPending ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span className="font-medium">Sending...</span>
            </>
          ) : (
            <>
              {isUser ? (
                <User className="h-3 w-3" />
              ) : (
                <Bot className="h-3 w-3" />
              )}
              <span>{formatMessageTime(timestamp)}</span>
            </>
          )}
        </p>
      </div>
      
      {isUser && (
        <div className="shrink-0 mt-1">
          <div className="h-8 w-8 rounded-lg bg-linear-to-br from-blue-100 to-blue-200 flex items-center justify-center shadow-sm border border-blue-200">
            <User className="h-4 w-4 text-blue-700" />
          </div>
        </div>
      )}
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;