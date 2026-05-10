'use client';

import { useRef, useEffect, useMemo } from 'react';
import { ChatLayout } from '@/components/ChatLayout';
import { MessageBubble } from '@/components/MessageBubble';
import { MessageInput } from '@/components/MessageInput';
import { TypingIndicator } from '@/components/TypingIndicator';
import { useChat } from '@/hooks/useChat';
import { ConversationProvider } from '@/contexts/ConversationContext';
import { PlaceCard } from '@/types/chat';

export default function Home() {
  const {
    messages,
    isStreaming,
    currentStreamingMessage,
    sendMessage,
    clearSession,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamingMessage]);

  // Extract all places from messages
  const allPlaces = useMemo(() => {
    const places: PlaceCard[] = [];
    messages.forEach((msg) => {
      if (msg.type === 'places' && msg.data?.places) {
        places.push(...msg.data.places);
      }
    });
    return places;
  }, [messages]);

  return (
    <ConversationProvider>
      <ChatLayout onNewChat={clearSession} places={allPlaces}>
      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-1 overscroll-contain">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <span className="text-5xl sm:text-6xl mb-3 sm:mb-4">🍜</span>
            <h2 className="text-xl sm:text-2xl font-bold mb-2 text-primary">Ăn gì cũng được</h2>
            <p className="text-sm sm:text-base text-secondary max-w-md">
              Xin chào! Tôi là trợ lý ẩm thực HCM. Hãy cho tôi biết bạn muốn ăn gì,
              ở đâu, budget bao nhiêu — tôi sẽ gợi ý cho bạn!
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Streaming message */}
        {isStreaming && currentStreamingMessage && (
          <div className="flex justify-start mb-3 sm:mb-4 animate-fadeIn px-2 sm:px-0">
            <div className="w-full max-w-full sm:max-w-[90%]">
              <div className="bg-tertiary rounded-2xl px-3 py-2 sm:px-4 sm:py-3">
                <p className="whitespace-pre-wrap text-sm sm:text-base break-words text-primary">{currentStreamingMessage}</p>
              </div>
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {isStreaming && !currentStreamingMessage && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <MessageInput onSend={sendMessage} isStreaming={isStreaming} />
    </ChatLayout>
    </ConversationProvider>
  );
}
