"""
Pydantic schemas for Conversation API
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    message_type: str | None = Field(None, description="Message type: text, places, dishes, place_detail")
    metadata: dict | None = Field(None, description="Additional metadata (places data, tool calls, etc.)")


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: UUID
    conversation_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: str = Field(..., max_length=500, description="Conversation title")


class ConversationCreate(ConversationBase):
    user_id: str | None = Field(None, description="User ID (nullable for anonymous)")
    first_message: str = Field(..., description="First user message to generate title")


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    is_archived: bool | None = None
    is_pinned: bool | None = None


class ConversationResponse(ConversationBase):
    id: UUID
    user_id: str | None
    title_generated_by: str
    is_archived: bool
    is_pinned: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    messages: list[MessageResponse] = []


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
    limit: int
    offset: int


class SearchResult(BaseModel):
    conversation: ConversationResponse
    matched_messages: list[MessageResponse]
    relevance_score: float | None = None
