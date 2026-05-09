"""
Chat Session Management with Redis
Short-term memory (session) + Long-term user profile
"""
import json
import re
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field
from redis.asyncio import Redis


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserProfile(BaseModel):
    """Long-term user preferences persisted across sessions."""
    user_id: str
    favorite_cuisines: list[str] = []
    disliked_cuisines: list[str] = []
    spicy_tolerance: int | None = None  # 0=none, 1=mild, 2=medium, 3=hot
    budget_preference: int | None = None
    favorite_districts: list[str] = []
    visit_count: int = 0
    last_seen: str = ""

    def to_prompt_dict(self) -> dict:
        return {
            "favorite_cuisines": self.favorite_cuisines,
            "disliked_cuisines": self.disliked_cuisines,
            "spicy_tolerance": self.spicy_tolerance,
            "budget_preference": self.budget_preference,
            "favorite_districts": self.favorite_districts,
        }


class ChatSession(BaseModel):
    """Chat session model — short-term conversational memory."""
    session_id: str
    user_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    budget_per_person: int | None = None
    people_count: int = 1
    vegetarian: bool = False
    halal: bool = False
    messages: list[dict] = []
    recommended_place_ids: list[str] = []
    mentioned_cuisines: list[str] = Field(default_factory=list)
    mentioned_districts: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


_memory_sessions: dict[str, str] = {}
_memory_profiles: dict[str, str] = {}

_DISLIKE_PATTERNS = [
    r'(?:không thích|ghét|dị ứng|không ăn được|hông thích)\s+(.+?)(?:\s*$|,|\.|!)',
    r'(?:tránh|skip|bỏ qua)\s+(.+?)(?:\s*$|,|\.|!)',
]

_LIKE_PATTERNS = [
    r'(?:thích|mê|ghiền|hay ăn|khoái)\s+(.+?)(?:\s*$|,|\.|!)',
]

_SPICY_PATTERNS = {
    0: [r'không\s*(?:ăn\s*)?cay', r'không\s*cay', r'nhạt'],
    1: [r'cay\s*(?:ít|nhẹ)', r'ít\s*cay'],
    2: [r'cay\s*vừa', r'cay\s*(?:bình\s*thường|ok)'],
    3: [r'cay\s*(?:nhiều|nồng|lắm)', r'rất\s*cay', r'siêu\s*cay'],
}

CUISINE_NAMES = [
    "phở", "bún bò", "cơm tấm", "bánh mì", "hủ tiếu", "bún đậu",
    "bún chả", "cơm gà", "lẩu", "nướng", "sushi", "pizza", "burger",
    "bánh xèo", "bún riêu", "mì quảng", "bánh cuốn", "cháo",
    "hải sản", "ốc", "dimsum", "ramen", "steak", "buffet",
    "bò kho", "xôi", "trà sữa", "cà phê", "chè", "kem",
    "mì cay", "tokbokki", "pasta", "gỏi cuốn", "chả giò",
]


class SessionService:
    def __init__(self, redis_client: Redis | None):
        self.redis = redis_client
        self.TTL = 3600 * 2
        self.PROFILE_TTL = 3600 * 24 * 90  # 90 days

    # ── Session CRUD ──

    async def get_or_create(self, session_id: str | None, user_id: str | None = None) -> ChatSession:
        if session_id:
            data = await self._get_raw(f"session:{session_id}")
            if data:
                return ChatSession(**json.loads(data))

        new_id = str(uuid4())
        session = ChatSession(
            session_id=new_id,
            user_id=user_id,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        await self.save(session)
        return session

    async def get(self, session_id: str) -> ChatSession | None:
        data = await self._get_raw(f"session:{session_id}")
        if data:
            return ChatSession(**json.loads(data))
        return None

    async def save(self, session: ChatSession):
        session.updated_at = now_iso()
        key = f"session:{session.session_id}"
        value = session.model_dump_json()
        if self.redis:
            await self.redis.setex(key, self.TTL, value)
        else:
            _memory_sessions[key] = value

    async def delete(self, session_id: str):
        key = f"session:{session_id}"
        if self.redis:
            await self.redis.delete(key)
        else:
            _memory_sessions.pop(key, None)

    async def _get_raw(self, key: str) -> str | None:
        if self.redis:
            return await self.redis.get(key)
        return _memory_sessions.get(key)

    async def add_message(self, session_id: str, role: str, content: str | dict):
        session = await self.get_or_create(session_id)
        session.messages.append({"role": role, "content": content})
        if len(session.messages) > 20:
            session.messages = session.messages[-20:]
        await self.save(session)

    async def update_location(self, session_id: str, lat: float, lng: float):
        session = await self.get_or_create(session_id)
        session.lat = lat
        session.lng = lng
        await self.save(session)

    async def add_recommended_place(self, session_id: str, place_id: str):
        session = await self.get_or_create(session_id)
        if place_id not in session.recommended_place_ids:
            session.recommended_place_ids.append(place_id)
        await self.save(session)

    async def update_context_from_message(self, session_id: str, user_message: str):
        session = await self.get_or_create(session_id)
        message_lower = user_message.lower()

        # Budget
        budget_patterns = [
            r'(?:dưới|under|max|tối đa)\s*(\d+)(?:k|nghìn|ngàn)',
            r'(?:khoảng|around|~)\s*(\d+)(?:k|nghìn|ngàn)',
            r'(\d+)(?:k|nghìn|ngàn)',
            r'(\d{2,3})\.?(\d{3})',
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) == 2:
                    budget = int(match.group(1)) * 1000 + int(match.group(2))
                else:
                    budget = int(match.group(1))
                    if budget < 1000:
                        budget *= 1000
                session.budget_per_person = budget
                break

        # People count
        people_patterns = [
            r'(\d+)\s*người', r'nhóm\s*(\d+)', r'đi\s*(\d+)',
        ]
        for pattern in people_patterns:
            match = re.search(pattern, message_lower)
            if match:
                count = int(match.group(1))
                if 1 <= count <= 20:
                    session.people_count = count
                break

        # Dietary
        if any(k in message_lower for k in ["ăn chay", "đồ chay", "món chay", "vegetarian", "chay"]):
            session.vegetarian = True
        if "halal" in message_lower:
            session.halal = True

        # Track mentioned cuisines (short-term memory)
        for cuisine in CUISINE_NAMES:
            if cuisine in message_lower and cuisine not in session.mentioned_cuisines:
                session.mentioned_cuisines.append(cuisine)

        # Track mentioned districts
        from app.rag.query_understanding import DISTRICT_PATTERNS
        for pattern, district_name in DISTRICT_PATTERNS:
            if re.search(pattern, message_lower) and district_name not in session.mentioned_districts:
                session.mentioned_districts.append(district_name)

        await self.save(session)
        return session

    # ── User Profile (long-term memory) ──

    async def get_profile(self, user_id: str) -> UserProfile:
        data = await self._get_raw(f"profile:{user_id}")
        if data:
            return UserProfile(**json.loads(data))
        return UserProfile(user_id=user_id, last_seen=now_iso())

    async def save_profile(self, profile: UserProfile):
        profile.last_seen = now_iso()
        key = f"profile:{profile.user_id}"
        value = profile.model_dump_json()
        if self.redis:
            await self.redis.setex(key, self.PROFILE_TTL, value)
        else:
            _memory_profiles[key] = value

    async def learn_from_message(self, user_id: str | None, message: str):
        """Extract long-term preferences from user message and update profile."""
        if not user_id:
            return
        msg = message.lower().strip()
        profile = await self.get_profile(user_id)
        changed = False

        # Detect dislikes
        for pattern in _DISLIKE_PATTERNS:
            match = re.search(pattern, msg)
            if match:
                item = match.group(1).strip()
                for cuisine in CUISINE_NAMES:
                    if cuisine in item and cuisine not in profile.disliked_cuisines:
                        profile.disliked_cuisines.append(cuisine)
                        if cuisine in profile.favorite_cuisines:
                            profile.favorite_cuisines.remove(cuisine)
                        changed = True

        # Detect likes
        for pattern in _LIKE_PATTERNS:
            match = re.search(pattern, msg)
            if match:
                item = match.group(1).strip()
                for cuisine in CUISINE_NAMES:
                    if cuisine in item and cuisine not in profile.favorite_cuisines:
                        profile.favorite_cuisines.append(cuisine)
                        if cuisine in profile.disliked_cuisines:
                            profile.disliked_cuisines.remove(cuisine)
                        changed = True

        # Detect spicy tolerance
        for level, patterns in _SPICY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg):
                    profile.spicy_tolerance = level
                    changed = True
                    break

        # Detect budget preference (only if explicitly stated as habitual)
        budget_habit = re.search(r'(?:thường|hay)\s+(?:ăn|đi ăn)\s+(?:khoảng|tầm)\s*(\d+)\s*(?:k|nghìn)', msg)
        if budget_habit:
            val = int(budget_habit.group(1))
            if val < 1000:
                val *= 1000
            profile.budget_preference = val
            changed = True

        # Detect favorite districts
        from app.rag.query_understanding import DISTRICT_PATTERNS
        fav_district = re.search(r'(?:thường|hay)\s+(?:ăn|đi ăn)\s+(?:ở|tại|khu)\s+', msg)
        if fav_district:
            for pattern, district_name in DISTRICT_PATTERNS:
                if re.search(pattern, msg) and district_name not in profile.favorite_districts:
                    profile.favorite_districts.append(district_name)
                    changed = True

        if changed:
            profile.visit_count += 1
            await self.save_profile(profile)

    async def learn_from_interaction(self, user_id: str | None, place_data: dict, interaction: str):
        """Learn from user actions: viewed detail, favorited, ordered from a place."""
        if not user_id:
            return
        profile = await self.get_profile(user_id)
        changed = False

        dishes = place_data.get("dishes") or place_data.get("dish_names") or []
        district = place_data.get("district", "")

        if interaction in ("favorite", "detail_view"):
            for dish in dishes:
                dish_lower = dish.lower()
                for cuisine in CUISINE_NAMES:
                    if cuisine in dish_lower and cuisine not in profile.favorite_cuisines:
                        profile.favorite_cuisines.append(cuisine)
                        changed = True
            if district and district not in profile.favorite_districts:
                profile.favorite_districts.append(district)
                changed = True

        if changed:
            profile.visit_count += 1
            await self.save_profile(profile)
