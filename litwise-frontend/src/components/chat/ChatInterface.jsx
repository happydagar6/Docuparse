'use client';

import React, { useState, useRef, useLayoutEffect, startTransition, useMemo, useEffectEvent, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  Send,
  Bot,
  FileText,
  Loader2,
  MessageCircle,
  ChevronDown,
  X,
  History,
} from 'lucide-react';
import { toast } from 'sonner';
import { useChatMessages, useChatSessions, useCreateChatSession, useDeleteChatSession } from '@/lib/react-query';
import { chatApi } from '@/lib/chat-api';
import ChatMessage from './ChatMessage';
import ChatSessions from './ChatSessions';
import { FormattedContent } from '@/components/ui/formatted-content';

const ChatInterface = ({ paper }) => {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [message, setMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sources, setSources] = useState([]);
  const [showMobileSessions, setShowMobileSessions] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [failedMessageIds, setFailedMessageIds] = useState(new Set());
  const [pendingMessageId, setPendingMessageId] = useState(null);
  
  // AbortController for stopping generation
  const abortControllerRef = useRef(null);
  
  // Query hooks
  const { data: sessions = [], refetch: refetchSessions } = useChatSessions(paper.id);
  const { data: messages = [], refetch: refetchMessages } = useChatMessages(activeSessionId);
  const createSessionMutation = useCreateChatSession();
  const deleteSessionMutation = useDeleteChatSession();

  // Track optimistic messages separately to avoid reset issues
  const [optimisticUserMessage, setOptimisticUserMessage] = useState(null);
  
  // Track if we should auto-scroll (only when user sends a new message)
  const shouldScrollRef = useRef(false);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // Combine actual messages with optimistic message
  const displayMessages = useMemo(() => {
    let allMessages = [...messages];
    
    // Add optimistic message if it exists and isn't already in messages
    if (optimisticUserMessage) {
      const existsInMessages = messages.some(msg => msg.id === optimisticUserMessage.id);
      if (!existsInMessages) {
        allMessages.push(optimisticUserMessage);
      }
    }
    
    // Enrich messages with pending and failed states
    return allMessages.map(msg => ({
      ...msg,
      isPending: msg.id === pendingMessageId,
      isFailed: failedMessageIds.has(msg.id)
    }));
  }, [messages, optimisticUserMessage, pendingMessageId, failedMessageIds]);

  // Auto-scroll to bottom using useLayoutEffect for better performance
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Manual scroll to bottom
  const forceScrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollButton(false);
  }, []);

  // React 19.2: useEffectEvent for scroll checking without dependency issues
  const isUserNearBottom = useEffectEvent(() => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (container) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        return scrollHeight - scrollTop - clientHeight < 100;
      }
    }
    return true; // Default to true if we can't detect
  });

  // Handle new messages - only scroll when user just sent a message
  useLayoutEffect(() => {
    if (shouldScrollRef.current && displayMessages.length > 0) {
      scrollToBottom();
      shouldScrollRef.current = false;
    }
  }, [displayMessages.length, scrollToBottom]);

  // Handle streaming message updates with throttling
  useLayoutEffect(() => {
    if (isStreaming && streamingMessage) {
      // Check user position and update button state only occasionally
      if (streamingMessage.length % 50 === 0) { // Check every 50 characters
        const nearBottom = isUserNearBottom();
        
        if (nearBottom) {
          // Scroll to bottom
          messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        }
        // Update button state outside the effect using setTimeout to avoid cascading renders
        setTimeout(() => {
          setShowScrollButton(!nearBottom);
        }, 0);
      } else if (streamingMessage.length < 50) {
        // For the first few characters, ensure we're scrolled to bottom
        const nearBottom = isUserNearBottom();
        if (nearBottom) {
          messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        }
      }
    }
  }, [streamingMessage, isStreaming]);

  // React 19.2: useEffectEvent for focus handling without dependencies
  const handleAutoFocus = useEffectEvent(() => {
    if (!isStreaming && activeSessionId) {
      startTransition(() => {
        inputRef.current?.focus();
      });
    }
  });

  useLayoutEffect(() => {
    handleAutoFocus();
  }, []);

  const handleCreateSession = async () => {
    try {
      const newSession = await createSessionMutation.mutateAsync({
        paperId: paper.id,
        title: `Chat Session ${sessions.length + 1}`,
      });
      setActiveSessionId(newSession.id);
      toast.success('New chat session created');
    } catch (error) {
      toast.error('Failed to create chat session');
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSessionMutation.mutateAsync(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
      toast.success('Chat session deleted');
    } catch (error) {
      toast.error('Failed to delete chat session');
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim() || isStreaming || !activeSessionId) return;

    const userMessage = message;
    const optimisticId = `optimistic-${Date.now()}`;
    const optimisticMessage = {
      id: optimisticId,
      content: userMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
      session_id: activeSessionId,
      isPending: true
    };

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    // Mark that we should scroll to bottom (user initiated action)
    shouldScrollRef.current = true;

    // Add optimistic message immediately (doesn't reset like useOptimistic)
    setOptimisticUserMessage(optimisticMessage);
    setPendingMessageId(optimisticId);
    setMessage('');
    setIsStreaming(true);
    setStreamingMessage('');
    setSources([]);

    try {
      await chatApi.streamChat(
        activeSessionId, 
        userMessage, 
        (chunk) => {
          // Inline callback for handling stream chunks
          if (chunk.type === 'token' && chunk.content) {
            setStreamingMessage(prev => prev + chunk.content);
            // Clear pending state once we get first response
            if (pendingMessageId) {
              setPendingMessageId(null);
            }
          } else if (chunk.type === 'sources' && chunk.sources) {
            setSources(chunk.sources);
          } else if (chunk.type === 'complete') {
            // Reset streaming state but keep messages visible until refetch completes
            setIsStreaming(false);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            
            // Refetch messages, then clear optimistic/streaming state
            setTimeout(async () => {
              await refetchMessages();
              // Only clear after refetch completes so there's no flash
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 300);
          } else if (chunk.type === 'aborted') {
            // Handle user-initiated abort
            toast.info('Generation stopped', {
              description: 'AI response was stopped by user'
            });
            // Reset streaming state
            setIsStreaming(false);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            
            // Refetch messages, then clear optimistic/streaming state
            setTimeout(async () => {
              await refetchMessages();
              // Only clear after refetch completes so there's no flash
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 300);
          } else if (chunk.type === 'error') {
            toast.error(chunk.error);
            // Reset all streaming-related state
            setIsStreaming(false);
            setStreamingMessage('');
            setSources([]);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            // Mark message as failed
            setFailedMessageIds(prev => new Set([...prev, optimisticId]));
          }
        },
        abortControllerRef.current.signal // Pass abort signal
      );
    } catch (error) {
      console.error('Chat error:', error);
      toast.error('Failed to send message', {
        description: 'Click to retry',
        action: {
          label: 'Retry',
          onClick: () => {
            setMessage(userMessage);
            // Remove failed state
            setFailedMessageIds(prev => {
              const newSet = new Set(prev);
              newSet.delete(optimisticId);
              return newSet;
            });
          },
        },
      });
      // Reset all streaming-related state
      setIsStreaming(false);
      setStreamingMessage('');
      setSources([]);
      setShowScrollButton(false);
      setPendingMessageId(null);
      abortControllerRef.current = null;
      // Don't clear optimistic message on error - keep it visible with failed state
      // Mark message as failed
      setFailedMessageIds(prev => new Set([...prev, optimisticId]));
    }
  };

  // Handle stopping generation
  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      toast.info('Stopping generation...', {
        duration: 2000
      });
    }
  }, []);

  // Handle message retry - defined after handleSendMessage to avoid hoisting issues
  const handleRetryMessage = async (failedMessage) => {
    setFailedMessageIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(failedMessage.id);
      return newSet;
    });
    
    // Resend the message
    setMessage(failedMessage.content);
    await handleSendMessage();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!paper) {
    return (
      <Card className="h-[600px] flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Select a paper to start chatting</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="h-full flex flex-col md:grid md:grid-cols-4 gap-4">
      {/* Sessions Sidebar - Hidden on mobile, collapsible */}
      <Card className="hidden md:flex md:col-span-1 flex-col">
        <CardHeader className="pb-3 shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Chat Sessions</CardTitle>
            <Button
              size="sm"
              onClick={handleCreateSession}
              disabled={createSessionMutation.isLoading}
            >
              {createSessionMutation.isLoading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <MessageCircle className="h-3 w-3" />
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-hidden">
          <ChatSessions
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSessionSelect={setActiveSessionId}
            onSessionDelete={handleDeleteSession}
            isDeleting={deleteSessionMutation.isLoading}
          />
        </CardContent>
      </Card>

      {/* Chat Area */}
      <Card className="flex-1 md:col-span-3 flex flex-col overflow-hidden">
        <CardHeader className="pb-2 shrink-0 p-2 md:p-4 border-b">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm md:text-base flex items-center gap-2">
              <Bot className="h-4 w-4" />
              <span className="truncate max-w-[150px] md:max-w-none">Chat</span>
              {activeSessionId && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {sessions.find(s => s.id === activeSessionId)?.title}
                </Badge>
              )}
            </CardTitle>
            
            {/* Mobile Sessions Button */}
            <div className="flex items-center gap-2 md:hidden">
              <Sheet open={showMobileSessions} onOpenChange={setShowMobileSessions}>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm">
                    <History className="h-4 w-4 mr-1" />
                    Sessions
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-[280px] p-0">
                  <SheetHeader className="p-4 border-b">
                    <SheetTitle className="flex items-center justify-between">
                      Chat Sessions
                      <Button
                        size="sm"
                        onClick={handleCreateSession}
                        disabled={createSessionMutation.isLoading}
                      >
                        {createSessionMutation.isLoading ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <MessageCircle className="h-3 w-3" />
                        )}
                      </Button>
                    </SheetTitle>
                  </SheetHeader>
                  <div className="flex-1 overflow-hidden">
                    <ChatSessions
                      sessions={sessions}
                      activeSessionId={activeSessionId}
                      onSessionSelect={(id) => {
                        setActiveSessionId(id);
                        setShowMobileSessions(false);
                      }}
                      onSessionDelete={handleDeleteSession}
                      isDeleting={deleteSessionMutation.isLoading}
                    />
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col min-h-0 p-0">
          {!activeSessionId ? (
            <div className="flex-1 flex items-center justify-center p-4">
              <div className="text-center text-muted-foreground">
                <MessageCircle className="mx-auto h-10 w-10 md:h-12 md:w-12 mb-4 opacity-50" />
                <p className="text-sm md:text-base">Create or select a chat session to begin</p>
                <Button 
                  className="mt-4" 
                  size="sm"
                  onClick={handleCreateSession}
                  disabled={createSessionMutation.isLoading}
                >
                  Start New Chat
                </Button>
              </div>
            </div>
          ) : (
            <>
              {/* Messages Area with proper flex and overflow */}
              <div className="flex-1 min-h-0 overflow-hidden relative">
                <ScrollArea 
                  className="h-full px-3 md:px-4" 
                  ref={scrollContainerRef}
                >
                  <div className="space-y-4 py-3 md:py-4 max-w-3xl mx-auto">
                    {displayMessages.map((msg) => (
                      <ChatMessage key={msg.id} message={msg} onRetry={handleRetryMessage} />
                    ))}
                    
                    {isStreaming && (
                      <div className="flex gap-3">
                        <div className="shrink-0">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Bot className="h-4 w-4 text-primary" />
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="bg-muted rounded-lg p-3">
                            <div className="streaming-content text-sm">
                              {streamingMessage ? (
                                <>
                                  <FormattedContent content={streamingMessage} />
                                  <span className="animate-pulse">|</span>
                                </>
                              ) : (
                                <div className="flex flex-col gap-2">
                                  <div className="flex items-center gap-2 text-muted-foreground">
                                    <Loader2 className="h-3 w-3 md:h-4 md:w-4 animate-spin" />
                                    <span className="text-xs md:text-sm">🔍 Searching...</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-muted-foreground ml-4 md:ml-6">
                                    <span className="text-xs md:text-sm animate-pulse">Reasoning...</span>
                                  </div>
                                </div>
                              )}
                            </div>
                            {sources.length > 0 && (
                              <div className="mt-2 md:mt-3 pt-2 md:pt-3 border-t">
                                <p className="text-xs text-muted-foreground mb-1 md:mb-2">Sources:</p>
                                <div className="space-y-1">
                                  {sources.map((source, idx) => (
                                    <div key={idx} className="text-xs bg-background rounded p-2">
                                      <p className="font-medium">Page {source.page}</p>
                                      <p className="text-muted-foreground line-clamp-2">{source.content}</p>
                                      <p className="text-xs text-blue-600">
                                        Relevance: {(source.relevance_score * 100).toFixed(1)}%
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>
                
                {/* Scroll to bottom button - appears when user scrolls up during streaming */}
                {showScrollButton && (
                  <div className="absolute bottom-3 right-3 md:bottom-4 md:right-4 z-10">
                    <Button
                      size="sm"
                      onClick={forceScrollToBottom}
                      className="rounded-full shadow-lg bg-primary hover:bg-primary/90 h-8 md:h-auto"
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-xs">AI is typing</span>
                        <ChevronDown className="w-3 h-3 md:w-4 md:h-4" />
                      </div>
                    </Button>
                  </div>
                )}
              </div>

              <Separator className="shrink-0" />
              
              {/* Input Area - Claude-like styling */}
              <div className="p-3 md:p-4 shrink-0 bg-background">
                <div className="max-w-3xl mx-auto">
                  <div className="flex gap-2 items-end">
                    <Input
                      ref={inputRef}
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask anything about this paper..."
                      disabled={isStreaming}
                      className="flex-1 text-base py-3 px-4 rounded-xl border-2 focus:border-primary"
                    />
                    {isStreaming ? (
                      <Button
                        onClick={handleStopGeneration}
                        variant="destructive"
                        size="icon"
                        className="h-11 w-11 rounded-xl shrink-0"
                        title="Stop generation"
                      >
                        <X className="h-5 w-5" />
                      </Button>
                    ) : (
                      <Button
                        onClick={handleSendMessage}
                        disabled={!message.trim()}
                        size="icon"
                        className="h-11 w-11 rounded-xl shrink-0"
                      >
                        <Send className="h-5 w-5" />
                      </Button>
                  )}
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ChatInterface;