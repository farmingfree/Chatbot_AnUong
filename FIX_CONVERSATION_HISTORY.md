# 🔧 Fix: Conversation History không hoạt động

## ❌ Vấn đề hiện tại

1. **Conversation không được tạo khi chat mới**
   - API endpoint trả về 404
   - Sidebar không hiển thị conversations

2. **Dark mode styling đã fix** ✅
   - Text colors đã được thêm
   - Button hover states đã fix

## ✅ Giải pháp

### Bước 1: Restart Backend (BẮT BUỘC)

Backend cần restart để load conversation router mới.

**Cách 1: Dùng script tự động**
```bash
# Double-click file này:
restart_backend.bat
```

**Cách 2: Manual**
```bash
# 1. Stop backend hiện tại (Ctrl+C trong terminal đang chạy backend)

# 2. Start lại backend
cd apps/api
uvicorn app.main:app --reload
```

### Bước 2: Verify API hoạt động

Sau khi restart, test API:

```bash
# Test 1: List conversations (should return empty list, not 404)
curl http://localhost:8000/api/conversations

# Expected: {"conversations":[],"total":0,"limit":50,"offset":0}
# NOT: {"detail":"Not Found"}

# Test 2: Health check
curl http://localhost:8000/health

# Expected: {"status":"ok","db":"connected",...}
```

### Bước 3: Test trên Frontend

1. **Mở browser:** http://localhost:3000
2. **Gửi tin nhắn:** "Tìm quán phở ngon"
3. **Kiểm tra:**
   - Console log có `conversation_id` event
   - Sidebar xuất hiện conversation mới
   - Title tự động generate

## 🔍 Debug nếu vẫn không hoạt động

### Check 1: Backend logs
```bash
# Xem logs khi gửi message
# Should see:
# - "Creating conversation..."
# - "Conversation created: <uuid>"
# - "Saving message to conversation..."
```

### Check 2: Database
```bash
cd apps/api
python -c "
from app.database import AsyncSessionLocal
from sqlalchemy import text
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT COUNT(*) FROM conversations'))
        count = result.scalar()
        print(f'Conversations in DB: {count}')
        
        result = await db.execute(text('SELECT COUNT(*) FROM messages'))
        count = result.scalar()
        print(f'Messages in DB: {count}')

asyncio.run(check())
"
```

### Check 3: Frontend console
```javascript
// Open browser console (F12)
// Should see:
// - "conversation_id event received: <uuid>"
// - "Conversation saved to localStorage"
```

### Check 4: Network tab
```
1. Open DevTools → Network tab
2. Send a message
3. Look for:
   - POST /api/chat/stream
   - Response should include: data: {"type":"conversation_id","conversation_id":"..."}
```

## 📊 Expected Flow

```
User sends message
    ↓
Backend receives request
    ↓
Check if conversation_id exists
    ↓ (NO)
Create new conversation
    ↓
Generate title from first message
    ↓
Save to database
    ↓
Stream conversation_id to frontend
    ↓
Frontend receives event
    ↓
Save to localStorage
    ↓
Update ConversationContext
    ↓
Sidebar shows new conversation
```

## 🐛 Common Issues

### Issue 1: "404 Not Found" khi call API
**Cause:** Backend chưa restart
**Fix:** Restart backend (see Bước 1)

### Issue 2: Conversation tạo nhưng không hiển thị
**Cause:** Frontend không load conversations
**Fix:** 
```javascript
// Check ConversationContext
// Should call loadConversations() on mount
```

### Issue 3: Title không generate
**Cause:** TitleGenerationService lỗi
**Fix:** Check backend logs, fallback to "Cuộc trò chuyện mới"

### Issue 4: Dark mode vẫn sai màu
**Cause:** Tailwind classes chưa apply
**Fix:** 
```bash
cd apps/web
npm run dev  # Restart frontend
```

## ✅ Verification Checklist

- [ ] Backend restart thành công
- [ ] API `/api/conversations` trả về 200 (không phải 404)
- [ ] Gửi message tạo conversation mới
- [ ] Sidebar hiển thị conversation
- [ ] Title tự động generate
- [ ] Search hoạt động
- [ ] Rename/Delete hoạt động
- [ ] Dark mode styling đúng

## 🚀 Quick Test Script

```bash
# Run this after restarting backend
python test_conversations.py
```

Expected output:
```
============================================================
Testing Conversation History API
============================================================

1. List conversations:
   Status: 200
   Total: 0 conversations

2. Create new conversation:
   Status: 200
   Created: Tìm quán phở ngon ở quận 1
   ID: <uuid>

3. Get conversation messages:
   Status: 200
   Messages: 1
   - [user] Tìm quán phở ngon ở quận 1...

...
```

## 📝 Notes

- Conversation tự động tạo khi gửi message đầu tiên
- Title generate từ message đầu tiên (max 100 chars)
- Messages được save vào cả Redis (session) và PostgreSQL (conversation)
- Frontend load conversations từ API, không dùng localStorage nữa

---

**TL;DR: Restart backend là bước quan trọng nhất! 🔄**
