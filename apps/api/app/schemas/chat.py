from pydantic import BaseModel, ConfigDict
from app.schemas.place import PlaceCard
from app.schemas.dish import DishCard


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "tool"
    content: str | list
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    lat: float | None = None
    lng: float | None = None
    session_id: str | None = None
    user_id: str | None = None
    conversation_id: str | None = None  # New: link to persistent conversation


class ChatResponse(BaseModel):
    message: str
    tool_calls: list | None = None
    places: list[PlaceCard] | None = None
    dishes: list[DishCard] | None = None
