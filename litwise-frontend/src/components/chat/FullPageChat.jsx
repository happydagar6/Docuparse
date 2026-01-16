/**
 * Full-Page Chat Component
 * 
 * Mobile-optimized chat interface that occupies entire viewport
 * Features:
 * - Responsive layout (mobile-first)
 * - Fixed input area at bottom
 * - Scrollable message area
 * - Adaptive message bubbles
 * - Session management via drawer/sidebar
 */

'use client';

import React, { useState, useRef, useLayoutEffect, startTransition, useMemo, useEffectEvent, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
  Menu,
} from 'lucide-react';
import { toast } from 'sonner';
import { useChatMessages, useChatSessions, useCreateChatSession, useDeleteChatSession } from '@/lib/react-query';
import { chatApi } from '@/lib/chat-api';
import ChatSessions from './ChatSessions';
import InfiniteScrollChat from './InfiniteScrollChat';

const FullPageChat = ({ paper }) => {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [message, setMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sources, setSources] = useState([]);
  const [showMobileSessions, setShowMobileSessions] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [failedMessageIds, setFailedMessageIds] = useState(new Set());
  const [pendingMessageId, setPendingMessageId] = useState(null);
  const textareaRef = useRef(null);
  
  // AbortController for stopping generation
  const abortControllerRef = useRef(null);
  
  // Query hooks
  const { data: sessions = [], refetch: refetchSessions } = useChatSessions(paper.id);
  const { data: messages = [], refetch: refetchMessages } = useChatMessages(activeSessionId);
  const createSessionMutation = useCreateChatSession();
  const deleteSessionMutation = useDeleteChatSession();

  // Track optimistic messages separately
  const [optimisticUserMessage, setOptimisticUserMessage] = useState(null);
  
  // Track if we should auto-scroll
  const shouldScrollRef = useRef(false);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // Combine actual messages with optimistic message
  const displayMessages = useMemo(() => {
    let allMessages = [...messages];
    
    if (optimisticUserMessage) {
      const existsInMessages = messages.some(msg => msg.id === optimisticUserMessage.id);
      if (!existsInMessages) {
        allMessages.push(optimisticUserMessage);
      }
    }
    
    return allMessages.map(msg => ({
      ...msg,
      isPending: msg.id === pendingMessageId,
      isFailed: failedMessageIds.has(msg.id)
    }));
  }, [messages, optimisticUserMessage, pendingMessageId, failedMessageIds]);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Manual scroll to bottom
  const forceScrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollButton(false);
  }, []);

  // Check if user is near bottom
  const isUserNearBottom = useEffectEvent(() => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (container) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        return scrollHeight - scrollTop - clientHeight < 100;
      }
    }
    return true;
  });

  // Handle new messages
  useLayoutEffect(() => {
    if (shouldScrollRef.current && displayMessages.length > 0) {
      scrollToBottom();
      shouldScrollRef.current = false;
    }
  }, [displayMessages.length, scrollToBottom]);

  // Handle streaming message updates
  useLayoutEffect(() => {
    if (isStreaming && streamingMessage) {
      if (streamingMessage.length % 50 === 0) {
        const nearBottom = isUserNearBottom();
        
        if (nearBottom) {
          messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        }
        setTimeout(() => {
          setShowScrollButton(!nearBottom);
        }, 0);
      } else if (streamingMessage.length < 50) {
        const nearBottom = isUserNearBottom();
        if (nearBottom) {
          messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        }
      }
    }
  }, [streamingMessage, isStreaming]);

  // Auto-focus input
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

    abortControllerRef.current = new AbortController();
    shouldScrollRef.current = true;

    setOptimisticUserMessage(optimisticMessage);
    setPendingMessageId(optimisticId);
    setMessage('');
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    setIsStreaming(true);
    setStreamingMessage('');
    setSources([]);

    try {
      await chatApi.streamChat(
        activeSessionId, 
        userMessage, 
        (chunk) => {
          if (chunk.type === 'token' && chunk.content) {
            setStreamingMessage(prev => prev + chunk.content);
            if (pendingMessageId) {
              setPendingMessageId(null);
            }
          } else if (chunk.type === 'sources' && chunk.sources) {
            setSources(chunk.sources);
          } else if (chunk.type === 'complete') {
            setIsStreaming(false);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            
            setTimeout(async () => {
              try {
                await refetchMessages();
              } catch (err) {
                console.error('Failed to refetch messages:', err);
              }
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 100);
          } else if (chunk.type === 'aborted') {
            toast.info('Generation stopped', {
              description: 'AI response was stopped by user'
            });
            setIsStreaming(false);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            
            setTimeout(async () => {
              try {
                await refetchMessages();
              } catch (err) {
                console.error('Failed to refetch messages:', err);
              }
              setStreamingMessage('');
              setSources([]);
              setOptimisticUserMessage(null);
            }, 100);
          } else if (chunk.type === 'error') {
            toast.error(chunk.error);
            setIsStreaming(false);
            setStreamingMessage('');
            setSources([]);
            setShowScrollButton(false);
            setPendingMessageId(null);
            abortControllerRef.current = null;
            setFailedMessageIds(prev => new Set([...prev, optimisticId]));
          }
        },
        abortControllerRef.current.signal
      );
    } catch (error) {
      console.error('Chat error:', error);
      
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
              setFailedMessageIds(prev => {
                const newSet = new Set(prev);
                newSet.delete(optimisticId);
                return newSet;
              });
            },
          },
        });
      }
      setIsStreaming(false);
      setStreamingMessage('');
      setSources([]);
      setShowScrollButton(false);
      setPendingMessageId(null);
      abortControllerRef.current = null;
      setFailedMessageIds(prev => new Set([...prev, optimisticId]));
    }
  };

  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      toast.info('Stopping generation...', {
        duration: 2000
      });
    }
  }, []);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleMessageChange = (e) => {
    const newMessage = e.target.value;
    setMessage(newMessage);
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 150);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  };

  if (!paper) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50">
        <div className="text-center text-muted-foreground p-6">
          <FileText className="mx-auto h-16 w-16 mb-4 opacity-50" />
          <p className="text-lg">Select a paper to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col md:flex-row overflow-hidden bg-linear-to-b from-white to-slate-50/50">
      {/* Desktop Sidebar - Sessions */}
      <div className="hidden md:flex md:w-80 lg:w-96 flex-col border-r border-slate-200/60 bg-white shadow-sm">
        <div className="shrink-0 p-4 border-b border-slate-200/50 bg-linear-to-b from-slate-50/50 to-white">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-slate-900">Chat Sessions</h2>
            <Button
              size="sm"
              onClick={handleCreateSession}
              disabled={createSessionMutation.isLoading}
              className="h-9 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors"
            >
              {createSessionMutation.isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <MessageCircle className="h-4 w-4 mr-1.5" />
                  <span className="text-sm">New</span>
                </>
              )}
            </Button>
          </div>
          
          {/* Active session indicator */}
          {activeSessionId && (
            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200 truncate max-w-full">
              {sessions.find(s => s.id === activeSessionId)?.title}
            </Badge>
          )}
        </div>
        
        <div className="flex-1 overflow-hidden">
          <ChatSessions
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSessionSelect={setActiveSessionId}
            onSessionDelete={handleDeleteSession}
            isDeleting={deleteSessionMutation.isLoading}
          />
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header */}
        <div className="shrink-0 md:hidden bg-white border-b border-slate-200/50 p-3 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <Sheet open={showMobileSessions} onOpenChange={setShowMobileSessions}>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" className="h-9 rounded-lg">
                  <Menu className="h-4 w-4 mr-1.5" />
                  <span className="text-xs">Sessions</span>
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-[85vw] sm:w-[320px] p-0 flex flex-col">
                <SheetTitle className="sr-only">Chat Sessions</SheetTitle>
                <SheetHeader className="p-4 border-b border-slate-200/50 bg-linear-to-b from-slate-50/50 to-white shrink-0">
                  <div className="flex items-start gap-2 pb-3 border-b border-slate-200/30">
                    <FileText className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-slate-500 font-medium">Discussing</p>
                      <p className="text-sm font-semibold text-slate-900 line-clamp-2">{paper?.title || 'Document'}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between pt-3">
                    <span className="font-semibold text-slate-900 text-sm">Sessions</span>
                    <Button
                      size="sm"
                      onClick={handleCreateSession}
                      disabled={createSessionMutation.isLoading}
                      className="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs"
                    >
                      {createSessionMutation.isLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <>
                          <MessageCircle className="h-3.5 w-3.5 mr-1" />
                          New
                        </>
                      )}
                    </Button>
                  </div>
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

            <div className="flex-1 min-w-0 flex items-center gap-2">
              <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-linear-to-br from-blue-500 to-cyan-500 shrink-0">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-semibold text-slate-900 truncate">
                {activeSessionId ? sessions.find(s => s.id === activeSessionId)?.title || 'AI Chat' : 'AI Chat'}
              </span>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        {!activeSessionId ? (
          <div className="flex-1 flex items-center justify-center p-6 bg-linear-to-br from-slate-50 to-white">
            <div className="text-center max-w-md">
              <div className="flex items-center justify-center h-20 w-20 rounded-2xl bg-linear-to-br from-blue-100 to-cyan-100 mx-auto mb-6 shadow-sm">
                <MessageCircle className="h-10 w-10 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Start a Conversation</h3>
              <p className="text-sm text-slate-600 mb-8 leading-relaxed">
                Create or select a chat session to begin discussing this paper with AI
              </p>
              <Button 
                onClick={handleCreateSession}
                disabled={createSessionMutation.isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white h-11 px-8 rounded-xl font-medium shadow-md hover:shadow-lg transition-all"
              >
                {createSessionMutation.isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>+ Start New Chat</>
                )}
              </Button>
            </div>
          </div>
        ) : (
          <>
            {/* Messages Container - Scrollable */}
            <div className="flex-1 min-h-0 overflow-hidden relative">
              <InfiniteScrollChat
                sessionId={activeSessionId}
                isStreaming={isStreaming}
                streamingMessage={streamingMessage}
                sources={sources}
                pageSize={20}
                optimisticUserMessage={optimisticUserMessage}
                displayMessages={displayMessages}
              />
              
              {/* Scroll to bottom button */}
              {showScrollButton && (
                <div className="absolute bottom-4 right-4 z-10 animate-in fade-in slide-in-from-bottom-2">
                  <Button
                    size="sm"
                    onClick={forceScrollToBottom}
                    className="rounded-full shadow-lg bg-blue-600 hover:bg-blue-700 text-white h-10 px-4"
                  >
                    <ChevronDown className="w-4 h-4 mr-1" />
                    <span className="text-sm">New message</span>
                  </Button>
                </div>
              )}
            </div>

            {/* Input Area - Fixed at bottom */}
            <div className="shrink-0 border-t border-slate-200/50 bg-white p-3 md:p-4 shadow-lg">
              <div className="max-w-4xl mx-auto">
                <div className="flex gap-2 md:gap-3 items-end">
                  <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={handleMessageChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask anything about this paper..."
                    disabled={isStreaming}
                    rows={1}
                    className="flex-1 text-sm md:text-base py-3 px-4 rounded-xl border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 bg-white shadow-sm hover:border-slate-400 transition-all placeholder:text-slate-400 resize-none overflow-y-auto max-h-[150px]"
                    style={{ minHeight: '44px' }}
                  />
                  {isStreaming ? (
                    <Button
                      onClick={handleStopGeneration}
                      variant="destructive"
                      size="icon"
                      className="h-11 w-11 rounded-xl shrink-0 bg-red-600 hover:bg-red-700 shadow-md"
                      title="Stop generation"
                    >
                      <X className="h-5 w-5" />
                    </Button>
                  ) : (
                    <Button
                      onClick={handleSendMessage}
                      disabled={!message.trim()}
                      size="icon"
                      className="h-11 w-11 rounded-xl shrink-0 bg-blue-600 hover:bg-blue-700 text-white shadow-md disabled:opacity-40 disabled:cursor-not-allowed transition-all"
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
      </div>
    </div>
  );
};

export default FullPageChat;
