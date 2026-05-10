export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  isPinned: boolean;
  messageCount: number;
}

export interface ConversationStore {
  conversations: Conversation[];
  activeConversationId: string | null;
}
