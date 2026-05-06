"""
Chat Session Management with Redis
Stores conversation context, user preferences, and message history
"""
import json
import re
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel
from redis.asyncio import Redis


def now_iso() -> str:
    """Get current time in ISO format"""
    return datetime.now(timezone.utc).isoformat()


class ChatSession(BaseModel):
    """Chat session model with conversation context"""
    session_id: str
    user_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    budget_per_person: int | None = None
    people_count: int = 1
    vegetarian: bool = False
    halal: bool = False
    messages: list[dict] = []  # OpenAI format, max 20 messages
    recommended_place_ids: list[str] = []  # Avoid re-recommending
    created_at: str
    updated_at: str


# In-memory session store (fallback when Redis unavailable)
_memory_sessions: dict[str, str] = {}


class SessionService:
    """Service for managing chat sessions in Redis (with in-memory fallback)"""
    
    def __init__(self, redis_client: Redis | None):
        self.redis = redis_client
        self.TTL = 3600 * 2  # 2 hours
    
    async def get_or_create(self, session_id: str | None, user_id: str | None = None) -> ChatSession:
        """Get existing session or create new one"""
        if session_id:
            data = await self._get_raw(f"session:{session_id}")
            if data:
                return ChatSession(**json.loads(data))
        
        # Create new session
        new_id = str(uuid4())
        session = ChatSession(
            session_id=new_id,
            user_id=user_id,
            created_at=now_iso(),
            updated_at=now_iso()
        )
        await self.save(session)
        return session
    
    async def get(self, session_id: str) -> ChatSession | None:
        """Get session by ID"""
        data = await self._get_raw(f"session:{session_id}")
        if data:
            return ChatSession(**json.loads(data))
        return None
    
    async def save(self, session: ChatSession):
        """Save session"""
        session.updated_at = now_iso()
        key = f"session:{session.session_id}"
        value = session.model_dump_json()
        if self.redis:
            await self.redis.setex(key, self.TTL, value)
        else:
            _memory_sessions[key] = value
    
    async def delete(self, session_id: str):
        """Delete session"""
        key = f"session:{session_id}"
        if self.redis:
            await self.redis.delete(key)
        else:
            _memory_sessions.pop(key, None)
    
    async def _get_raw(self, key: str) -> str | None:
        """Get raw value from Redis or memory"""
        if self.redis:
            return await self.redis.get(key)
        return _memory_sessions.get(key)
    
    async def add_message(self, session_id: str, role: str, content: str | dict):
        """Add message to session history"""
        session = await self.get_or_create(session_id)
        session.messages.append({"role": role, "content": content})
        
        # Keep only last 20 messages to avoid context overflow
        if len(session.messages) > 20:
            session.messages = session.messages[-20:]
        
        await self.save(session)
    
    async def update_location(self, session_id: str, lat: float, lng: float):
        """Update user location in session"""
        session = await self.get_or_create(session_id)
        session.lat = lat
        session.lng = lng
        await self.save(session)
    
    async def add_recommended_place(self, session_id: str, place_id: str):
        """Track recommended places to avoid duplicates"""
        session = await self.get_or_create(session_id)
        if place_id not in session.recommended_place_ids:
            session.recommended_place_ids.append(place_id)
        await self.save(session)
    
    async def update_context_from_message(self, session_id: str, user_message: str):
        """Extract and update context from user message"""
        session = await self.get_or_create(session_id)
        message_lower = user_message.lower()
        
        # Extract budget: "dưới 50k", "45 nghìn", "300.000", "khoảng 100k"
        budget_patterns = [
            r'(?:dưới|under|max|tối đa)\s*(\d+)(?:k|nghìn|ngàn)',  # dưới 50k
            r'(?:khoảng|around|~)\s*(\d+)(?:k|nghìn|ngàn)',  # khoảng 50k
            r'(\d+)(?:k|nghìn|ngàn)',  # 50k
            r'(\d{2,3})\.?(\d{3})',  # 50.000 or 50000
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) == 2:  # Format like 50.000
                    budget = int(match.group(1)) * 1000 + int(match.group(2))
                else:
                    budget = int(match.group(1))
                    # Convert k/nghìn to actual number
                    if 'k' in message_lower or 'nghìn' in message_lower or 'ngàn' in message_lower:
                        budget = budget * 1000
                
                session.budget_per_person = budget
                break
        
        # Extract people count: "2 người", "đi 3 người", "nhóm 4", "4 người"
        people_patterns = [
            r'(\d+)\s*người',  # 2 người
            r'nhóm\s*(\d+)',  # nhóm 4
            r'đi\s*(\d+)',  # đi 3
            r'(\d+)\s*(?:ng|người|pax)',  # 4 ng
        ]
        
        for pattern in people_patterns:
            match = re.search(pattern, message_lower)
            if match:
                count = int(match.group(1))
                if 1 <= count <= 20:  # Reasonable range
                    session.people_count = count
                break
        
        # Detect vegetarian: "ăn chay", "đồ chay", "món chay", "vegetarian"
        vegetarian_keywords = ['ăn chay', 'đồ chay', 'món chay', 'vegetarian', 'chay']
        if any(keyword in message_lower for keyword in vegetarian_keywords):
            session.vegetarian = True
        
        # Detect halal: "halal", "đồ halal", "món halal"
        halal_keywords = ['halal', 'đồ halal', 'món halal']
        if any(keyword in message_lower for keyword in halal_keywords):
            session.halal = True
        
        await self.save(session)
        return session
