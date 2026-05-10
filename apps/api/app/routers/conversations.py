"""
Conversations API Router
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages,
    ConversationListResponse,
    MessageCreate,
    MessageResponse,
    SearchResult,
)
from app.services.conversation_service import ConversationService
from app.services.title_generation import improve_title_background
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new conversation with auto-generated title.
    Title is generated using rule-based approach first,
    then improved with LLM in background.
    """
    service = ConversationService(db)

    # Create conversation with rule-based title
    conversation = await service.create_conversation(
        user_id=data.user_id,
        first_message=data.first_message
    )

    # Add first user message
    await service.add_message(
        conversation_id=conversation.id,
        role="user",
        content=data.first_message,
        message_type="text"
    )

    # Schedule background task to improve title with LLM
    background_tasks.add_task(
        improve_title_background,
        conversation_id=str(conversation.id),
        messages=[{"role": "user", "content": data.first_message}],
        llm_client=LLMClient(),
        conversation_service=service
    )

    return conversation


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str | None = Query(None, description="User ID (null for anonymous)"),
    limit: int = Query(50, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    include_archived: bool = Query(False, description="Include archived conversations"),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversations for a user with pagination.
    Pinned conversations appear first.
    """
    service = ConversationService(db)
    conversations, total = await service.get_conversations(
        user_id=user_id,
        limit=limit,
        offset=offset,
        include_archived=include_archived
    )

    return ConversationListResponse(
        conversations=conversations,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation by ID with all messages"""
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, load_messages=True)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update conversation (title, archive, pin status)"""
    service = ConversationService(db)
    conversation = await service.update_conversation(conversation_id, data)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete conversation and all its messages"""
    service = ConversationService(db)
    success = await service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return None


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a conversation with pagination"""
    service = ConversationService(db)

    # Verify conversation exists
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await service.get_messages(conversation_id, limit=limit, offset=offset)
    return messages


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add message to conversation"""
    service = ConversationService(db)

    # Verify conversation exists
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = await service.add_message(
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
        message_type=data.message_type,
        metadata=data.metadata
    )

    return message


@router.get("/search", response_model=list[SearchResult])
async def search_conversations(
    q: str = Query(..., min_length=1, description="Search query"),
    user_id: str | None = Query(None, description="User ID"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Search conversations by title and message content.
    Uses PostgreSQL full-text search.
    """
    service = ConversationService(db)
    results = await service.search_conversations(user_id=user_id, query=q, limit=limit)

    return [
        SearchResult(
            conversation=conv,
            matched_messages=messages,
            relevance_score=len(messages) if messages else None
        )
        for conv, messages in results
    ]
