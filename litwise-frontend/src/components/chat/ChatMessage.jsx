'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Bot, FileText, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { FormattedContent } from '@/components/ui/formatted-content';
import { Button } from '@/components/ui/button';

const ChatMessage = ({ message, onRetry }) => {
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

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="h-4 w-4 text-primary" />
          </div>
        </div>
      )}
      
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`rounded-lg p-3 ${
          isUser 
            ? message.isFailed
              ? 'bg-red-100 text-red-900 border-2 border-red-300 ml-auto'
              : 'bg-primary text-primary-foreground ml-auto' 
            : 'bg-muted'
        }`}>
          <div className="wrap-break-word">
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <FormattedContent content={message.content} />
            )}
          </div>
          
          {/* Failed message indicator */}
          {message.isFailed && (
            <div className="mt-2 pt-2 border-t border-red-300 flex items-center gap-2 text-xs">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <span className="text-red-700">Failed to send</span>
              {onRetry && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onRetry(message)}
                  className="h-6 px-2 text-xs hover:bg-red-200"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              )}
            </div>
          )}
          
          {/* Sources (only for assistant messages) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                <FileText className="h-3 w-3" />
                Sources:
              </p>
              <div className="space-y-1">
                {message.sources.map((source, idx) => (
                  <Card key={idx} className="p-2">
                    <div className="text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">Page {source.page}</span>
                        <Badge variant="outline" className="text-xs">
                          {(source.relevance_score * 100).toFixed(1)}% match
                        </Badge>
                      </div>
                      <p className="text-muted-foreground line-clamp-2">
                        {source.content}
                      </p>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Timestamp with pending state */}
        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
          {message.isPending ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              {isUser ? (
                <User className="h-3 w-3" />
              ) : (
                <Bot className="h-3 w-3" />
              )}
              {format(timestamp, 'MMM d, h:mm a')}
            </>
          )}
        </p>
      </div>
      
      {isUser && (
        <div className="shrink-0">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <User className="h-4 w-4 text-blue-600" />
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatMessage;