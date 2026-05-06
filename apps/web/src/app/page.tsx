'use client';

import { useRef, useEffect } from 'react';
import { ChatLayout } from '@/components/ChatLayout';
import { MessageBubble } from '@/components/MessageBubble';
import { MessageInput } from '@/components/MessageInput';
import { TypingIndicator } from '@/components/TypingIndicator';
import { useChat } from '@/hooks/useChat';

export default function Home() {
  const {
    messages,
    isStreaming,
    currentStreamingMessage,
    sendMessage,
    clearSession,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamingMessage]);

  return (
    <ChatLayout onNewChat={clearSession}>
      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <span className="text-6xl mb-4">🍜</span>
            <h2 className="text-2xl font-bold mb-2">Ăn gì cũng được</h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-md">
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
          <div className="flex justify-start mb-4 animate-fadeIn">
            <div className="w-full">
              <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-3">
                <p className="whitespace-pre-wrap">{currentStreamingMessage}</p>
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
  );
}
