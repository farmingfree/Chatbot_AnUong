'use client';

import { useState, useEffect, useCallback } from 'react';
import { Message, UserLocation } from '@/types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chat_session_id');
    if (savedSessionId) {
      setSessionId(savedSessionId);
      loadSessionHistory(savedSessionId);
    }

    // Get user location
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => {
          console.error('Error getting location:', error);
          // Default to HCM center
          setUserLocation({ lat: 10.7769, lng: 106.7009 });
        }
      );
    } else {
      setUserLocation({ lat: 10.7769, lng: 106.7009 });
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      localStorage.setItem(`chat_messages_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  const loadSessionHistory = async (sid: string) => {
    try {
      // Try to load from backend first
      const response = await fetch(`${API_URL}/api/chat/session/${sid}/history`);
      if (response.ok) {
        const data = await response.json();
        const loadedMessages: Message[] = data.messages.map((msg: any, idx: number) => ({
          id: `${sid}-${idx}`,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(),
        }));
        setMessages(loadedMessages);
        return;
      }
    } catch (error) {
      console.error('Error loading session history from backend:', error);
    }

    // Fallback to localStorage
    try {
      const savedMessages = localStorage.getItem(`chat_messages_${sid}`);
      if (savedMessages) {
        const parsed = JSON.parse(savedMessages);
        setMessages(parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })));
      }
    } catch (error) {
      console.error('Error loading session history from localStorage:', error);
    }
  };

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setCurrentStreamingMessage('');

      try {
        const response = await fetch(`${API_URL}/api/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            messages: [{ role: 'user', content }],
            lat: userLocation?.lat,
            lng: userLocation?.lng,
            session_id: sessionId,
          }),
        });

        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let streamingTextContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);

              if (data === '[DONE]') {
                // Finalize streaming message
                if (streamingTextContent) {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `assistant-${Date.now()}`,
                      role: 'assistant',
                      content: streamingTextContent,
                      type: 'text',
                      timestamp: new Date(),
                    },
                  ]);
                }
                setIsStreaming(false);
                setCurrentStreamingMessage('');
                continue;
              }

              try {
                const parsed = JSON.parse(data);

                if (parsed.type === 'session_id') {
                  setSessionId(parsed.session_id);
                  localStorage.setItem('chat_session_id', parsed.session_id);
                } else if (parsed.type === 'text') {
                  streamingTextContent += parsed.content;
                  setCurrentStreamingMessage(streamingTextContent);
                } else if (parsed.type === 'places') {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `places-${Date.now()}`,
                      role: 'assistant',
                      content: '',
                      type: 'places',
                      data: parsed.data,
                      timestamp: new Date(),
                    },
                  ]);
                } else if (parsed.type === 'dishes') {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `dishes-${Date.now()}`,
                      role: 'assistant',
                      content: '',
                      type: 'dishes',
                      data: parsed.data,
                      timestamp: new Date(),
                    },
                  ]);
                } else if (parsed.type === 'place_detail') {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `place-detail-${Date.now()}`,
                      role: 'assistant',
                      content: '',
                      type: 'place_detail',
                      data: parsed.data,
                      timestamp: new Date(),
                    },
                  ]);
                } else if (parsed.type === 'error') {
                  console.error('Stream error:', parsed.message);
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `error-${Date.now()}`,
                      role: 'assistant',
                      content: `Lỗi: ${parsed.message}`,
                      timestamp: new Date(),
                    },
                  ]);
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
            timestamp: new Date(),
          },
        ]);
        setIsStreaming(false);
        setCurrentStreamingMessage('');
      }
    },
    [isStreaming, sessionId, userLocation]
  );

  const clearSession = useCallback(() => {
    if (sessionId) {
      fetch(`${API_URL}/api/chat/session/${sessionId}`, { method: 'DELETE' }).catch(console.error);
      localStorage.removeItem('chat_session_id');
      localStorage.removeItem(`chat_messages_${sessionId}`);
    }
    setSessionId(null);
    setMessages([]);
    setCurrentStreamingMessage('');
  }, [sessionId]);

  return {
    messages,
    isStreaming,
    sessionId,
    userLocation,
    currentStreamingMessage,
    sendMessage,
    clearSession,
    setUserLocation,
  };
}
