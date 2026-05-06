from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.place import PlaceCard


class UserPreferences(BaseModel):
    """User preferences for food recommendations"""
    budget_per_person: int | None = None  # VNĐ
    vegetarian: bool = False
    favorite_districts: list[str] = []
    disliked_dishes: list[str] = []
    dietary_notes: str | None = None


class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None


class UserCreate(UserBase):
    provider: str  # "google"
    provider_id: str  # Google sub ID


class UserResponse(UserBase):
    id: UUID
    provider: str | None = None
    preferences: dict = {}
    created_at: datetime
    last_active_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(UserResponse):
    """Extended user info for /me endpoint"""
    pass


class PreferencesUpdate(BaseModel):
    """Partial update for user preferences"""
    budget_per_person: int | None = None
    vegetarian: bool | None = None
    favorite_districts: list[str] | None = None
    disliked_dishes: list[str] | None = None
    dietary_notes: str | None = None


class FavoriteRequest(BaseModel):
    place_id: UUID


class FavoriteResponse(BaseModel):
    favorited: bool
    place_id: UUID


class FavoritesListResponse(BaseModel):
    favorites: list[PlaceCard]
    total: int
