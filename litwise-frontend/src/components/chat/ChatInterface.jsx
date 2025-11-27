'use client';

import React, { useState, useRef, useLayoutEffect, useOptimistic, startTransition, useMemo, useEffectEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Send,
  Bot,
  FileText,
  Loader2,
  MessageCircle,
  ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';
import { useChatMessages, useChatSessions, useCreateChatSession, useDeleteChatSession } from '@/lib/react-query';
import { chatApi } from '@/lib/chat-api';
import ChatMessage from './ChatMessage';
import ChatSessions from './ChatSessions';

const ChatInterface = ({ paper }) => {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [message, setMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sources, setSources] = useState([]);
  const [showScrollButton, setShowScrollButton] = useState(false);
  
  // React 19.2: useOptimistic for optimistic UI updates
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    [],
    (state, newMessage) => [...state, newMessage]
  );
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // Query hooks
  const { data: sessions = [], refetch: refetchSessions } = useChatSessions(paper.id);
  const { data: messages = [], refetch: refetchMessages } = useChatMessages(activeSessionId);
  const createSessionMutation = useCreateChatSession();
  const deleteSessionMutation = useDeleteChatSession();

  // Combine actual messages with optimistic messages using useMemo
  const displayMessages = useMemo(() => {
    return [...messages, ...optimisticMessages];
  }, [messages, optimisticMessages]);

  // Auto-scroll to bottom using useLayoutEffect for better performance
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Manual scroll to bottom
  const forceScrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollButton(false);
  };

  // Check if user is near bottom without causing re-renders
  const isUserNearBottom = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (container) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        return scrollHeight - scrollTop - clientHeight < 100;
      }
    }
    return true; // Default to true if we can't detect
  };

  // Handle new messages (not during streaming)
  useLayoutEffect(() => {
    if (!isStreaming && displayMessages.length > 0) {
      scrollToBottom();
      setShowScrollButton(false);
    }
  }, [displayMessages.length, isStreaming]);

  // Handle streaming start/end
  useLayoutEffect(() => {
    if (!isStreaming) {
      setShowScrollButton(false);
    }
  }, [isStreaming]);

  // Handle streaming message updates with throttling
  useLayoutEffect(() => {
    if (isStreaming && streamingMessage) {
      // Check user position and update button state only occasionally
      if (streamingMessage.length % 50 === 0) { // Check every 50 characters
        const nearBottom = isUserNearBottom();
        
        if (nearBottom) {
          setShowScrollButton(false);
          // Scroll to bottom
          messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        } else {
          setShowScrollButton(true);
        }
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
    const optimisticMessage = {
      id: `optimistic-${Date.now()}`,
      content: userMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
      session_id: activeSessionId
    };

    // React 19.2: Add optimistic message immediately
    startTransition(() => {
      addOptimisticMessage(optimisticMessage);
      setMessage('');
      setIsStreaming(true);
      setStreamingMessage('');
      setSources([]);
    });

    try {
      await chatApi.streamChat(activeSessionId, userMessage, (chunk) => {
        if (chunk.type === 'token' && chunk.content) {
          setStreamingMessage(prev => prev + chunk.content);
        } else if (chunk.type === 'sources' && chunk.sources) {
          setSources(chunk.sources);
        } else if (chunk.type === 'complete') {
          setIsStreaming(false);
          setStreamingMessage('');
          setShowScrollButton(false); // Hide scroll button when streaming ends
          refetchMessages();
        } else if (chunk.type === 'error') {
          toast.error(chunk.error);
          setIsStreaming(false);
          setStreamingMessage('');
          setShowScrollButton(false); // Hide scroll button on error
        }
      });
    } catch (error) {
      toast.error('Failed to send message');
      setIsStreaming(false);
      setStreamingMessage('');
      setShowScrollButton(false); // Hide scroll button on error
    }
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
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 h-[calc(100vh-280px)] min-h-[600px]">
      {/* Sessions Sidebar */}
      <Card className="md:col-span-1 flex flex-col">
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
      <Card className="md:col-span-3 flex flex-col overflow-hidden">
        <CardHeader className="pb-3 shrink-0">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Chat with `{paper.title}`
            {activeSessionId && (
              <Badge variant="secondary" className="ml-2">
                {sessions.find(s => s.id === activeSessionId)?.title}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
          {!activeSessionId ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <MessageCircle className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>Create or select a chat session to begin</p>
                <Button 
                  className="mt-4" 
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
              <div className="flex-1 overflow-hidden relative">
                <ScrollArea 
                  className="h-full px-4" 
                  ref={scrollContainerRef}
                >
                  <div className="space-y-4 py-4">
                    {displayMessages.map((msg) => (
                      <ChatMessage key={msg.id} message={msg} />
                    ))}
                    
                    {isStreaming && (
                      <div className="flex gap-3">
                        <div className="shrink-0">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Bot className="h-4 w-4 text-primary" />
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="bg-muted rounded-lg p-3">
                            <div className="whitespace-pre-wrap">
                              {streamingMessage}
                              <span className="animate-pulse">|</span>
                            </div>
                            {sources.length > 0 && (
                              <div className="mt-3 pt-3 border-t">
                                <p className="text-xs text-muted-foreground mb-2">Sources:</p>
                                <div className="space-y-1">
                                  {sources.map((source, idx) => (
                                    <div key={idx} className="text-xs bg-background rounded p-2">
                                      <p className="font-medium">Page {source.page}</p>
                                      <p className="text-muted-foreground">{source.content}</p>
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
                  <div className="absolute bottom-4 right-4 z-10">
                    <Button
                      size="sm"
                      onClick={forceScrollToBottom}
                      className="rounded-full shadow-lg bg-primary hover:bg-primary/90"
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-xs">AI is typing</span>
                        <ChevronDown className="w-4 h-4" />
                      </div>
                    </Button>
                  </div>
                )}
              </div>

              <Separator className="shrink-0" />
              
              {/* Input Area */}
              <div className="p-4 shrink-0">
                <div className="flex gap-2">
                  <Input
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask questions about this paper..."
                    disabled={isStreaming}
                    className="flex-1"
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={!message.trim() || isStreaming}
                    size="icon"
                  >
                    {isStreaming ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Press Enter to send • Shift+Enter for new line
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ChatInterface;