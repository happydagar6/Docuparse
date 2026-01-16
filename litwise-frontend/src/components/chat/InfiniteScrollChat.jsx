"use client";

import React, { useRef, useEffect, useCallback, useMemo, memo, useId } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";
import ChatMessage from "./ChatMessage";
import { useInfiniteMessages } from "@/hooks/useInifiniteMessages";

const InfiniteScrollChat = ({
  sessionId,
  onAddMessage,
  onUpdateMessage,
  isStreaming,
  streamingMessage,
  sources,
  pageSize = 20,
  optimisticUserMessage, // Add this prop from ChatInterface
  displayMessages: externalMessages, // Add this prop for external message management
}) => {
  const {
    messages,
    isLoading,
    hasMore,
    totalCount,
    error,
    loadOlder,
    addMessage,
    updateMessage,
    reset,
  } = useInfiniteMessages(sessionId, pageSize);

  const scrollContainerRef = useRef(null); // Reference to the scrollable container
  const messagesEndRef = useRef(null); // Reference to the end of messages for auto-scroll
  const observerRef = useRef(null); // Reference for IntersectionObserver
  const lastScrollHeightRef = useRef(0); // To track last scroll height for maintaining position
  const streamingId = useId(); // Generate unique ID for streaming message

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Scroll to bottom on initial load when user sends messages
  useEffect(() => {
    if (!isLoading && messages.length > 0 && !hasMore) {
      scrollToBottom(); // Only scroll if no more older messages
    }
  }, [messages.length, isLoading, hasMore, scrollToBottom]);

  // Interaction Observer for infinite scroll (load older messages when user scroll up)
  useEffect(() => {
    const sentinel = document.getElementById("scroll-sentinel");
    if (!sentinel) return; // No sentinel found

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          loadOlder();
        }
      },
      { threshold: 0.1, rootMargin: "100px" }
    );

    observerRef.current.observe(sentinel);

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, isLoading, loadOlder]);

  // Handle parent component message additions
  useEffect(() => {
    if (onAddMessage) {
      const unsubscribe = onAddMessage(() => addMessage);
      return unsubscribe;
    }
  }, [onAddMessage, addMessage]);

  // Display streaming message optimistically
  const displayMessages = useMemo(() => {
    // Use external messages if provided (from ChatInterface), otherwise use hook messages
    const baseMessages = externalMessages || messages;
    const allMessages = [...baseMessages];

    // Add optimistic user message if it exists and not already in messages
    if (optimisticUserMessage) {
      const existsInMessages = baseMessages.some(msg => msg.id === optimisticUserMessage.id);
      if (!existsInMessages) {
        allMessages.push(optimisticUserMessage);
      }
    }

    // Add streaming message if currently streaming
    if (isStreaming) {
      allMessages.push({
        id: `streaming-${streamingId}`,
        role: "assistant",
        content: streamingMessage,
        sources: sources || [],
        created_at: new Date().toISOString(),
        isPending: !streamingMessage, // Show reasoning indicator when no content yet
      });
    }
    return allMessages;
  }, [messages, externalMessages, optimisticUserMessage, isStreaming, streamingMessage, sources, streamingId]);

  return (
    <ScrollArea
      ref={scrollContainerRef}
      className="h-full w-full bg-white"
    >
      <div className="p-3 md:p-4 space-y-3 md:space-y-4">
        {/* Loading indicator for older messages */}
        {isLoading && messages.length === 0 && (
          <div className="flex justify-center items-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-600">Loading messages...</span>
          </div>
        )}

        {/* Scroll sentinel - triggers loading older messages */}
        {hasMore && messages.length > 0 && (
          <>
            <div id="scroll-sentinel" className="h-0" />
            {isLoading && (
              <div className="flex justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              </div>
            )}
          </>
        )}

        {/* Message list */}
        {displayMessages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            isStreaming={isStreaming}
            isPending={message.isPending}
            isFailed={message.isFailed}
          />
        ))}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} className="h-1" />

        {/* Error display */}
        {error && (
          <div className="text-red-600 text-xs md:text-sm p-2 md:p-3 bg-red-50 rounded border border-red-200">
            <span className="font-semibold">Error loading messages:</span> {error}
          </div>
        )}

        {/* Empty state */}
        {displayMessages.length === 0 && !isLoading && (
          <div className="text-center text-gray-500 py-8">
            No messages yet. Start chatting!
          </div>
        )}

        {/* Total count indicator */}
        {totalCount > 0 && (
          <div className="text-xs text-gray-400 text-center py-2">
            {displayMessages.length} of {totalCount} messages loaded
          </div>
        )}
      </div>
    </ScrollArea>
  );
};

export default memo(InfiniteScrollChat);
