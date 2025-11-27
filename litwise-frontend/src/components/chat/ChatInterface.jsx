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
  
  // React 19.2: useOptimistic for optimistic UI updates
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    [],
    (state, newMessage) => [...state, newMessage]
  );
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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

  useLayoutEffect(() => {
    scrollToBottom();
  }, [displayMessages, streamingMessage]);

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
          refetchMessages();
        } else if (chunk.type === 'error') {
          toast.error(chunk.error);
          setIsStreaming(false);
          setStreamingMessage('');
        }
      });
    } catch (error) {
      toast.error('Failed to send message');
      setIsStreaming(false);
      setStreamingMessage('');
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
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 h-[600px]">
      {/* Sessions Sidebar */}
      <Card className="md:col-span-1">
        <CardHeader className="pb-3">
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
        <CardContent className="p-0">
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
      <Card className="md:col-span-3 flex flex-col">
        <CardHeader className="pb-3">
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
        
        <CardContent className="flex-1 flex flex-col p-0">
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
              {/* Messages Area */}
              <ScrollArea className="flex-1 px-4">
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

              <Separator />
              
              {/* Input Area */}
              <div className="p-4">
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