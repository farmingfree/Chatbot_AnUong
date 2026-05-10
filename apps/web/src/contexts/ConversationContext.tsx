'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { Conversation, ConversationStore } from '@/types/conversation';
import { Message } from '@/types/chat';

interface ConversationContextType {
  conversations: Conversation[];
  activeConversationId: string | null;
  createConversation: () => string;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  togglePinConversation: (id: string) => void;
  switchConversation: (id: string) => void;
  updateConversationFromMessages: (id: string, messages: Message[]) => void;
  getConversationMessages: (id: string) => Message[];
}

const ConversationContext = createContext<ConversationContextType>({
  conversations: [],
  activeConversationId: null,
  createConversation: () => '',
  deleteConversation: () => {},
  renameConversation: () => {},
  togglePinConversation: () => {},
  switchConversation: () => {},
  updateConversationFromMessages: () => {},
  getConversationMessages: () => [],
});

const STORAGE_KEY = 'chat_conversations';
const MESSAGES_PREFIX = 'chat_messages_';

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Load conversations from localStorage on mount
  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed: ConversationStore = JSON.parse(stored);
        setConversations(parsed.conversations.map(c => ({
          ...c,
          timestamp: new Date(c.timestamp),
        })));
        setActiveConversationId(parsed.activeConversationId);
      } catch (error) {
        console.error('Error loading conversations:', error);
      }
    }

    // If no conversations exist, create a default one
    if (!stored || JSON.parse(stored).conversations.length === 0) {
      const newId = createNewConversation();
      setActiveConversationId(newId);
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (mounted && conversations.length > 0) {
      const store: ConversationStore = {
        conversations,
        activeConversationId,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    }
  }, [conversations, activeConversationId, mounted]);

  const createNewConversation = useCallback((): string => {
    const id = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newConv: Conversation = {
      id,
      title: 'Cuộc trò chuyện mới',
      lastMessage: '',
      timestamp: new Date(),
      isPinned: false,
      messageCount: 0,
    };
    setConversations(prev => [newConv, ...prev]);
    return id;
  }, []);

  const createConversation = useCallback((): string => {
    const id = createNewConversation();
    setActiveConversationId(id);
    return id;
  }, [createNewConversation]);

  const deleteConversation = useCallback((id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id));
    localStorage.removeItem(`${MESSAGES_PREFIX}${id}`);
    localStorage.removeItem(`chat_session_id_${id}`);

    // If deleting active conversation, switch to another
    if (activeConversationId === id) {
      setConversations(prev => {
        if (prev.length > 0) {
          setActiveConversationId(prev[0].id);
        } else {
          const newId = createNewConversation();
          setActiveConversationId(newId);
        }
        return prev;
      });
    }
  }, [activeConversationId, createNewConversation]);

  const renameConversation = useCallback((id: string, title: string) => {
    setConversations(prev =>
      prev.map(c => (c.id === id ? { ...c, title } : c))
    );
  }, []);

  const togglePinConversation = useCallback((id: string) => {
    setConversations(prev => {
      const updated = prev.map(c =>
        c.id === id ? { ...c, isPinned: !c.isPinned } : c
      );
      // Sort: pinned first, then by timestamp
      return updated.sort((a, b) => {
        if (a.isPinned && !b.isPinned) return -1;
        if (!a.isPinned && b.isPinned) return 1;
        return b.timestamp.getTime() - a.timestamp.getTime();
      });
    });
  }, []);

  const switchConversation = useCallback((id: string) => {
    setActiveConversationId(id);
  }, []);

  const updateConversationFromMessages = useCallback((id: string, messages: Message[]) => {
    if (messages.length === 0) return;

    const lastMsg = messages[messages.length - 1];
    const firstUserMsg = messages.find(m => m.role === 'user');

    // Auto-generate title from first user message
    let autoTitle = 'Cuộc trò chuyện mới';
    if (firstUserMsg && firstUserMsg.content) {
      const content = typeof firstUserMsg.content === 'string'
        ? firstUserMsg.content
        : JSON.stringify(firstUserMsg.content);
      autoTitle = content.slice(0, 40) + (content.length > 40 ? '...' : '');
    }

    setConversations(prev =>
      prev.map(c => {
        if (c.id === id) {
          // Only auto-update title if it's still the default
          const shouldUpdateTitle = c.title === 'Cuộc trò chuyện mới' && c.messageCount === 0;
          return {
            ...c,
            title: shouldUpdateTitle ? autoTitle : c.title,
            lastMessage: typeof lastMsg.content === 'string'
              ? lastMsg.content.slice(0, 60)
              : '',
            timestamp: new Date(),
            messageCount: messages.length,
          };
        }
        return c;
      })
    );
  }, []);

  const getConversationMessages = useCallback((id: string): Message[] => {
    try {
      const stored = localStorage.getItem(`${MESSAGES_PREFIX}${id}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        return parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
      }
    } catch (error) {
      console.error('Error loading messages for conversation:', id, error);
    }
    return [];
  }, []);

  return (
    <ConversationContext.Provider
      value={{
        conversations,
        activeConversationId,
        createConversation,
        deleteConversation,
        renameConversation,
        togglePinConversation,
        switchConversation,
        updateConversationFromMessages,
        getConversationMessages,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversations() {
  return useContext(ConversationContext);
}
