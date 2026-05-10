# Conversation History - Frontend Implementation TODO

## ✅ Completed (Backend)
- [x] Database models & migration
- [x] ConversationService with CRUD + search
- [x] Title generation (rule-based + LLM lazy)
- [x] API endpoints (/api/conversations/*)
- [x] Chat integration (save to conversations)
- [x] Database tables created successfully

## ⏳ Remaining (Frontend)

### 1. Update useChat Hook
**File:** `apps/web/src/hooks/useChat.ts`

Add conversation support:
```typescript
const [conversationId, setConversationId] = useState<string | null>(null);

// When sending message, include conversation_id
const sendMessage = async (content: string) => {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: 'POST',
    body: JSON.stringify({
      messages: [...],
      conversation_id: conversationId,  // Add this
      session_id: sessionId,
    })
  });

  // Listen for conversation_id event
  if (event.type === 'conversation_id') {
    setConversationId(event.conversation_id);
    localStorage.setItem('current_conversation_id', event.conversation_id);
  }
};
```

### 2. Update ConversationContext
**File:** `apps/web/src/contexts/ConversationContext.tsx`

Replace localStorage with API calls:
```typescript
// Fetch conversations from API
const fetchConversations = async () => {
  const res = await fetch(`${API_URL}/api/conversations?user_id=${userId}`);
  const data = await res.json();
  setConversations(data.conversations);
};

// Create new conversation
const createConversation = async (firstMessage: string) => {
  const res = await fetch(`${API_URL}/api/conversations`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, first_message: firstMessage })
  });
  return await res.json();
};

// Delete, rename, pin, archive - call API endpoints
```

### 3. Update ConversationSidebar
**File:** `apps/web/src/components/ConversationSidebar.tsx`

Add features:
- [x] Basic list (already exists)
- [ ] Search input with API call to `/api/conversations/search?q=...`
- [ ] Infinite scroll / pagination
- [ ] Loading skeletons
- [ ] Empty state

### 4. Update ChatLayout
**File:** `apps/web/src/components/ChatLayout.tsx`

- [ ] Integrate ConversationSidebar (already has placeholder)
- [ ] Pass conversations from ConversationContext
- [ ] Handle conversation switching

### 5. Update page.tsx
**File:** `apps/web/src/app/page.tsx`

- [ ] Wrap with ConversationContext provider
- [ ] Handle conversation routing (optional: /chat/[id])
- [ ] Load conversation messages when switching

## Quick Implementation Steps

1. **Test Backend First:**
```bash
# Start backend
cd apps/api && uvicorn app.main:app --reload

# Test API
curl http://localhost:8000/api/conversations
```

2. **Update Frontend (Priority Order):**
   - useChat.ts - Add conversation_id support (15 min)
   - ConversationContext.tsx - Replace localStorage with API (20 min)
   - ConversationSidebar.tsx - Add search (10 min)
   - ChatLayout.tsx - Integrate sidebar (5 min)
   - page.tsx - Add context provider (5 min)

3. **Test End-to-End:**
   - Create new chat
   - Send messages
   - Check sidebar updates
   - Switch conversations
   - Search conversations
   - Delete conversation

## Estimated Time: 1-2 hours for frontend

## Files to Modify:
- `apps/web/src/hooks/useChat.ts`
- `apps/web/src/contexts/ConversationContext.tsx`
- `apps/web/src/components/ConversationSidebar.tsx`
- `apps/web/src/components/ChatLayout.tsx`
- `apps/web/src/app/page.tsx`
