'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Bot, FileText } from 'lucide-react';
import { format } from 'date-fns';

const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.created_at);

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
            ? 'bg-primary text-primary-foreground ml-auto' 
            : 'bg-muted'
        }`}>
          <div className="whitespace-pre-wrap wrap-break-word">
            {message.content}
          </div>
          
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
        
        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
          {isUser ? (
            <User className="h-3 w-3" />
          ) : (
            <Bot className="h-3 w-3" />
          )}
          {format(timestamp, 'MMM d, h:mm a')}
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