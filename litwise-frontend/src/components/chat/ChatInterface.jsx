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
import InfiniteScrollChat from './InfiniteScrollChat';
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
            
            // Refetch messages to get fresh data from backend (cache invalidated)
            // Then clear optimistic/streaming state
            setTimeout(async () => {
              try {
                await refetchMessages();
              } catch (err) {
                console.error('Failed to refetch messages:', err);
              }
              // Clear streaming and optimistic message after refetch
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 100); // Reduced delay - messages should be available immediately
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
            
            // Refetch messages to get fresh data from backend (cache invalidated)
            setTimeout(async () => {
              try {
                await refetchMessages();
              } catch (err) {
                console.error('Failed to refetch messages:', err);
              }
              // Clear streaming and optimistic message after refetch
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 100);
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
      
      // Handle rate limit errors specifically
      if (error.status === 429) {
        const waitTime = error.retryAfter || 60;
        toast.error('Too Many Requests', {
          description: `Rate limit exceeded. Please wait ${waitTime} seconds before sending another message.`,
          duration: 5000,
        });
      } else {
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
      }
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
    <div className="h-full flex flex-col md:grid md:grid-cols-4 gap-3 md:gap-4">
      {/* Sessions Sidebar - Hidden on mobile, collapsible */}
      <Card className="hidden md:flex md:col-span-1 flex-col border-slate-200/60 shadow-sm hover:shadow-md transition-shadow">
        <CardHeader className="pb-3 shrink-0 border-b border-slate-200/50 bg-linear-to-b from-slate-50/50 to-white">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-slate-900">Chat Sessions</CardTitle>
            <Button
              size="sm"
              onClick={handleCreateSession}
              disabled={createSessionMutation.isLoading}
              className="h-8 w-8 p-0 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors"
            >
              {createSessionMutation.isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <MessageCircle className="h-4 w-4" />
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
      <Card className="flex-1 md:col-span-3 flex flex-col overflow-hidden border-slate-200/60 shadow-sm hover:shadow-md transition-shadow">
        <CardHeader className="pb-3 shrink-0 p-3 md:p-5 border-b border-slate-200/50 bg-linear-to-r from-white via-slate-50/50 to-white">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm md:text-base flex items-center gap-2 font-semibold text-slate-900">
              <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 shrink-0">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <span className="truncate max-w-[120px] md:max-w-none">AI Chat</span>
              {activeSessionId && (
                <Badge variant="outline" className="ml-2 text-xs bg-blue-50 text-blue-700 border-blue-200 font-medium">
                  {sessions.find(s => s.id === activeSessionId)?.title}
                </Badge>
              )}
            </CardTitle>
            
            {/* Mobile Sessions Button */}
            <div className="flex items-center gap-2 md:hidden">
              <Sheet open={showMobileSessions} onOpenChange={setShowMobileSessions}>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm" className="h-9 rounded-lg border-slate-200 hover:bg-slate-100">
                    <History className="h-4 w-4 mr-1.5" />
                    <span className="text-xs font-medium">Sessions</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-[280px] p-0 border-r border-slate-200/60">
                  <SheetHeader className="p-4 border-b border-slate-200/50 bg-linear-to-b from-slate-50/50 to-white sticky top-0 z-10">
                    <SheetTitle className="flex items-center justify-between text-slate-900">
                      <span className="font-semibold">Chat Sessions</span>
                      <Button
                        size="sm"
                        onClick={handleCreateSession}
                        disabled={createSessionMutation.isLoading}
                        className="h-8 w-8 p-0 rounded-lg bg-blue-600 hover:bg-blue-700"
                      >
                        {createSessionMutation.isLoading ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <MessageCircle className="h-3.5 w-3.5" />
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
            <div className="flex-1 flex items-center justify-center p-4 md:p-6">
              <div className="text-center max-w-sm">
                <div className="flex items-center justify-center h-16 w-16 rounded-2xl bg-linear-to-br from-blue-100 to-cyan-100 mx-auto mb-4 shadow-sm">
                  <MessageCircle className="h-8 w-8 text-blue-600" />
                </div>
                <h3 className="text-base md:text-lg font-semibold text-slate-900 mb-2">Start Chatting</h3>
                <p className="text-sm text-slate-600 mb-6">Create or select a chat session to begin discussing this paper with AI</p>
                <Button 
                  onClick={handleCreateSession}
                  disabled={createSessionMutation.isLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white h-10 px-6 rounded-lg font-medium transition-colors"
                >
                  {createSessionMutation.isLoading ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Starting...</>
                  ) : (
                    <>+ Start New Chat</>
                  )}
                </Button>
              </div>
            </div>
          ) : (
            <>
              {/* Messages Area - Using InfiniteScrollChat for pagination support */}
              <div className="flex-1 min-h-0 overflow-hidden relative bg-linear-to-b from-white via-slate-50/30 to-white">
                <InfiniteScrollChat
                  sessionId={activeSessionId}
                  isStreaming={isStreaming}
                  streamingMessage={streamingMessage}
                  sources={sources}
                  pageSize={20}
                  optimisticUserMessage={optimisticUserMessage}
                  displayMessages={displayMessages}
                />
                
                {/* Scroll to bottom button - appears when user scrolls up during streaming */}
                {showScrollButton && (
                  <div className="absolute bottom-4 right-4 z-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <Button
                      size="sm"
                      onClick={forceScrollToBottom}
                      className="rounded-full shadow-lg bg-blue-600 hover:bg-blue-700 text-white h-9 md:h-10 px-3 md:px-4 font-medium transition-all"
                    >
                      <ChevronDown className="w-4 h-4 mr-1" />
                      <span className="text-xs md:text-sm">New message</span>
                    </Button>
                  </div>
                )}
              </div>

              <Separator className="shrink-0 border-slate-200/50" />
              
              {/* Input Area - Modern styling */}
              <div className="p-3 md:p-4 lg:p-5 shrink-0 bg-linear-to-b from-white to-slate-50/50 border-t border-slate-200/40">
                <div className="max-w-4xl mx-auto">
                  <div className="flex gap-2 md:gap-3 items-end">
                    <Input
                      ref={inputRef}
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask anything about this paper..."
                      disabled={isStreaming}
                      className="flex-1 text-sm md:text-base py-3 px-4 rounded-xl border-1.5 border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-200 bg-white shadow-sm hover:border-slate-300 transition-colors placeholder:text-slate-500"
                    />
                    {isStreaming ? (
                      <Button
                        onClick={handleStopGeneration}
                        variant="destructive"
                        size="icon"
                        className="h-10 md:h-11 w-10 md:w-11 rounded-xl shrink-0 bg-red-600 hover:bg-red-700 shadow-sm transition-colors"
                        title="Stop generation"
                      >
                        <X className="h-5 w-5" />
                      </Button>
                    ) : (
                      <Button
                        onClick={handleSendMessage}
                        disabled={!message.trim()}
                        size="icon"
                        className="h-10 md:h-11 w-10 md:w-11 rounded-xl shrink-0 bg-blue-600 hover:bg-blue-700 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Send message"
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