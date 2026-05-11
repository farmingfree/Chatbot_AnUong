# 🔄 Conversation History Flow

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   useChat    │───▶│ ConversationContext │───▶│  Sidebar  │     │
│  │   Hook       │    │   (API calls)   │    │  Component │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                    │                     │            │
│         │ POST /chat/stream  │ GET /conversations  │            │
│         ▼                    ▼                     ▼            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/SSE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Chat Router  │───▶│ Conversation │───▶│   Database   │     │
│  │ /api/chat/*  │    │   Service    │    │  PostgreSQL  │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                    │                     │            │
│         │                    │                     │            │
│  ┌──────────────┐    ┌──────────────┐            │            │
│  │Conversations │───▶│    Title     │            │            │
│  │   Router     │    │  Generation  │            │            │
│  │/api/convs/*  │    │   Service    │            │            │
│  └──────────────┘    └──────────────┘            │            │
│                                                   │            │
└───────────────────────────────────────────────────┼────────────┘
                                                    │
                                                    ▼
                                    ┌──────────────────────────┐
                                    │   PostgreSQL Database    │
                                    ├──────────────────────────┤
                                    │  ┌──────────────────┐   │
                                    │  │  conversations   │   │
                                    │  │  - id (UUID)     │   │
                                    │  │  - title         │   │
                                    │  │  - user_id       │   │
                                    │  │  - created_at    │   │
                                    │  └──────────────────┘   │
                                    │           │              │
                                    │           │ 1:N          │
                                    │           ▼              │
                                    │  ┌──────────────────┐   │
                                    │  │    messages      │   │
                                    │  │  - id (UUID)     │   │
                                    │  │  - conversation_id│  │
                                    │  │  - role          │   │
                                    │  │  - content       │   │
                                    │  │  - extra_data    │   │
                                    │  └──────────────────┘   │
                                    └──────────────────────────┘
```

## 🔄 Message Flow (Step by Step)

### 1️⃣ User sends first message

```
User types: "Tìm quán phở ngon"
    │
    ▼
useChat.sendMessage()
    │
    ▼
POST /api/chat/stream
    {
      "messages": [{"role": "user", "content": "Tìm quán phở ngon"}],
      "session_id": "abc123",
      "conversation_id": null  ← First message, no conversation yet
    }
```

### 2️⃣ Backend creates conversation

```
Backend receives request
    │
    ▼
Check: conversation_id exists? → NO
    │
    ▼
ConversationService.create_conversation()
    │
    ├─▶ Generate title from message
    │   "Tìm quán phở ngon" → "Tìm quán phở ngon"
    │
    ├─▶ Save to database
    │   INSERT INTO conversations (id, title, user_id, ...)
    │
    └─▶ Return conversation object
        { id: "uuid-123", title: "Tìm quán phở ngon", ... }
```

### 3️⃣ Stream conversation_id to frontend

```
Backend streams SSE events:
    │
    ├─▶ data: {"type": "conversation_id", "conversation_id": "uuid-123"}
    │
    ├─▶ data: {"type": "text", "content": "Dạ, tôi sẽ tìm..."}
    │
    └─▶ data: [DONE]
```

### 4️⃣ Frontend receives and saves

```
useChat receives SSE event
    │
    ▼
if (event.type === 'conversation_id')
    │
    ├─▶ setConversationId(event.conversation_id)
    │
    ├─▶ localStorage.setItem('current_conversation_id', ...)
    │
    └─▶ ConversationContext.loadConversations()
            │
            ▼
        GET /api/conversations
            │
            ▼
        Update sidebar with new conversation
```

### 5️⃣ Subsequent messages

```
User sends second message: "Quận 1 nhé"
    │
    ▼
POST /api/chat/stream
    {
      "messages": [...],
      "conversation_id": "uuid-123"  ← Now we have conversation_id
    }
    │
    ▼
Backend saves message to existing conversation
    │
    ├─▶ ConversationService.add_message(
    │       conversation_id="uuid-123",
    │       role="user",
    │       content="Quận 1 nhé"
    │   )
    │
    └─▶ INSERT INTO messages (conversation_id, role, content, ...)
```

## 🎯 Key Points

### ✅ What Works Now
- ✅ Auto-create conversation on first message
- ✅ Auto-generate title from first message
- ✅ Save all messages to database
- ✅ Load conversations from API
- ✅ Search in conversations
- ✅ Rename/Delete conversations
- ✅ Dark mode styling

### ⚠️ What Needs Restart
- ⚠️ Backend must restart to load new router
- ⚠️ Without restart: API returns 404

### 🔧 How to Fix
```bash
# Stop backend (Ctrl+C)
cd apps/api
uvicorn app.main:app --reload
```

## 📝 Data Flow Summary

```
User Message
    ↓
Frontend (useChat)
    ↓
POST /api/chat/stream
    ↓
Backend (Chat Router)
    ↓
Create Conversation (if first message)
    ↓
Generate Title
    ↓
Save to PostgreSQL
    ↓
Stream conversation_id
    ↓
Frontend receives event
    ↓
Save to localStorage
    ↓
Load conversations from API
    ↓
Update Sidebar
    ↓
User sees conversation in sidebar ✅
```

## 🗄️ Database Schema

```sql
-- conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    title_generated_by VARCHAR(50),
    is_archived BOOLEAN DEFAULT FALSE,
    is_pinned BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW()
);

-- messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50),
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX ix_conversations_user_id ON conversations(user_id);
CREATE INDEX ix_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX ix_messages_created_at ON messages(created_at DESC);
```

## 🔍 Debugging Tips

### Check if backend loaded router
```bash
curl http://localhost:8000/api/conversations
# Should return: {"conversations":[],...}
# NOT: {"detail":"Not Found"}
```

### Check database
```bash
cd apps/api
python check_conversations_db.py
```

### Check frontend console
```javascript
// Open DevTools (F12) → Console
// Should see:
// "conversation_id event received: uuid-123"
```

### Check network
```
DevTools → Network → POST /api/chat/stream
Response should include:
data: {"type":"conversation_id","conversation_id":"..."}
```

---

**Remember: Backend restart is the key! 🔑**
