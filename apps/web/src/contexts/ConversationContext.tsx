'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { Conversation } from '@/types/conversation';
import { Message } from '@/types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ConversationContextType {
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  createConversation: (firstMessage: string) => Promise<string>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  togglePinConversation: (id: string) => Promise<void>;
  switchConversation: (id: string) => void;
  loadConversations: () => Promise<void>;
  searchConversations: (query: string) => Promise<void>;
}

const ConversationContext = createContext<ConversationContextType>({
  conversations: [],
  activeConversationId: null,
  isLoading: false,
  createConversation: async () => '',
  deleteConversation: async () => {},
  renameConversation: async () => {},
  togglePinConversation: async () => {},
  switchConversation: () => {},
  loadConversations: async () => {},
  searchConversations: async () => {},
});

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userId] = useState<string | null>(null); // TODO: Get from auth

  // Load conversations on mount
  useEffect(() => {
    loadConversations();

    // Load active conversation from localStorage
    const savedConvId = localStorage.getItem('current_conversation_id');
    if (savedConvId) {
      setActiveConversationId(savedConvId);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      params.append('limit', '50');

      const response = await fetch(`${API_URL}/api/conversations?${params}`);
      if (!response.ok) throw new Error('Failed to load conversations');

      const data = await response.json();
      setConversations(data.conversations.map((c: any) => ({
        id: c.id,
        title: c.title,
        lastMessage: '',
        timestamp: new Date(c.last_message_at),
        isPinned: c.is_pinned,
        messageCount: c.message_count,
      })));
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const createConversation = useCallback(async (firstMessage: string): Promise<string> => {
    try {
      const response = await fetch(`${API_URL}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          first_message: firstMessage,
        }),
      });

      if (!response.ok) throw new Error('Failed to create conversation');

      const data = await response.json();
      const newConv: Conversation = {
        id: data.id,
        title: data.title,
        lastMessage: firstMessage,
        timestamp: new Date(data.created_at),
        isPinned: false,
        messageCount: 1,
      };

      setConversations(prev => [newConv, ...prev]);
      setActiveConversationId(data.id);
      localStorage.setItem('current_conversation_id', data.id);

      return data.id;
    } catch (error) {
      console.error('Error creating conversation:', error);
      throw error;
    }
  }, [userId]);

  const deleteConversation = useCallback(async (id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete conversation');

      setConversations(prev => prev.filter(c => c.id !== id));

      // If deleting active conversation, switch to another
      if (activeConversationId === id) {
        const remaining = conversations.filter(c => c.id !== id);
        if (remaining.length > 0) {
          setActiveConversationId(remaining[0].id);
          localStorage.setItem('current_conversation_id', remaining[0].id);
        } else {
          setActiveConversationId(null);
          localStorage.removeItem('current_conversation_id');
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
      throw error;
    }
  }, [activeConversationId, conversations]);

  const renameConversation = useCallback(async (id: string, title: string) => {
    try {
      const response = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });

      if (!response.ok) throw new Error('Failed to rename conversation');

      setConversations(prev =>
        prev.map(c => (c.id === id ? { ...c, title } : c))
      );
    } catch (error) {
      console.error('Error renaming conversation:', error);
      throw error;
    }
  }, []);

  const togglePinConversation = useCallback(async (id: string) => {
    const conv = conversations.find(c => c.id === id);
    if (!conv) return;

    try {
      const response = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_pinned: !conv.isPinned }),
      });

      if (!response.ok) throw new Error('Failed to toggle pin');

      setConversations(prev =>
        prev.map(c => (c.id === id ? { ...c, isPinned: !c.isPinned } : c))
      );
    } catch (error) {
      console.error('Error toggling pin:', error);
      throw error;
    }
  }, [conversations]);

  const switchConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    localStorage.setItem('current_conversation_id', id);
  }, []);

  const searchConversations = useCallback(async (query: string) => {
    if (!query.trim()) {
      await loadConversations();
      return;
    }

    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('q', query);
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_URL}/api/conversations/search?${params}`);
      if (!response.ok) throw new Error('Failed to search conversations');

      const data = await response.json();
      setConversations(data.map((result: any) => ({
        id: result.conversation.id,
        title: result.conversation.title,
        lastMessage: '',
        timestamp: new Date(result.conversation.last_message_at),
        isPinned: result.conversation.is_pinned,
        messageCount: result.conversation.message_count,
      })));
    } catch (error) {
      console.error('Error searching conversations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId, loadConversations]);

  return (
    <ConversationContext.Provider
      value={{
        conversations,
        activeConversationId,
        isLoading,
        createConversation,
        deleteConversation,
        renameConversation,
        togglePinConversation,
        switchConversation,
        loadConversations,
        searchConversations,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversations() {
  return useContext(ConversationContext);
}
