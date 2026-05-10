"""
Conversation Service - CRUD operations and search for conversations
"""
import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)
from app.services.title_generation import generate_title_rule_based

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(
        self,
        user_id: str | None,
        first_message: str
    ) -> Conversation:
        """
        Create new conversation with auto-generated title from first message.
        Uses rule-based title generation for speed.
        """
        title = generate_title_rule_based(first_message)

        conversation = Conversation(
            user_id=user_id,
            title=title,
            title_generated_by="rule",
            message_count=0,
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(f"Created conversation {conversation.id} with title: {title}")
        return conversation

    async def get_conversations(
        self,
        user_id: str | None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False
    ) -> tuple[list[Conversation], int]:
        """
        Get conversations for a user with pagination.
        Returns (conversations, total_count).
        Pinned conversations appear first.
        """
        # Build query
        query = select(Conversation).where(Conversation.user_id == user_id)

        if not include_archived:
            query = query.where(Conversation.is_archived == False)

        # Order by pinned first, then by last_message_at
        query = query.order_by(
            desc(Conversation.is_pinned),
            desc(Conversation.last_message_at)
        )

        # Get total count
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )
        if not include_archived:
            count_query = count_query.where(Conversation.is_archived == False)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        conversations = result.scalars().all()

        return list(conversations), total

    async def get_conversation(
        self,
        conversation_id: str | UUID,
        load_messages: bool = False
    ) -> Conversation | None:
        """Get conversation by ID, optionally with messages"""
        query = select(Conversation).where(Conversation.id == conversation_id)

        if load_messages:
            query = query.options(selectinload(Conversation.messages))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_title(
        self,
        conversation_id: str | UUID,
        title: str,
        generated_by: str = "manual"
    ) -> Conversation | None:
        """Update conversation title"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        conversation.title = title
        conversation.title_generated_by = generated_by
        conversation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(f"Updated title for conversation {conversation_id}: {title}")
        return conversation

    async def update_conversation(
        self,
        conversation_id: str | UUID,
        update_data: ConversationUpdate
    ) -> Conversation | None:
        """Update conversation fields"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        if update_data.title is not None:
            conversation.title = update_data.title
            conversation.title_generated_by = "manual"

        if update_data.is_archived is not None:
            conversation.is_archived = update_data.is_archived

        if update_data.is_pinned is not None:
            conversation.is_pinned = update_data.is_pinned

        conversation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(conversation)

        return conversation

    async def delete_conversation(self, conversation_id: str | UUID) -> bool:
        """Delete conversation (cascade deletes messages)"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        await self.db.delete(conversation)
        await self.db.commit()

        logger.info(f"Deleted conversation {conversation_id}")
        return True

    async def add_message(
        self,
        conversation_id: str | UUID,
        role: str,
        content: str,
        message_type: str | None = None,
        metadata: dict | None = None
    ) -> Message:
        """Add message to conversation and update conversation metadata"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata,
        )

        self.db.add(message)

        # Update conversation
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.message_count += 1
            conversation.last_message_at = datetime.utcnow()
            conversation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(message)

        return message

    async def get_messages(
        self,
        conversation_id: str | UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[Message]:
        """Get messages for a conversation with pagination"""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_conversations(
        self,
        user_id: str | None,
        query: str,
        limit: int = 20
    ) -> list[tuple[Conversation, list[Message]]]:
        """
        Full-text search in conversation titles and message content.
        Returns list of (conversation, matched_messages) tuples.
        """
        # Search in titles
        title_search = (
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.title.ilike(f"%{query}%")
                )
            )
            .limit(limit)
        )

        # Search in message content using PostgreSQL full-text search
        message_search = (
            select(Message)
            .join(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    func.to_tsvector('simple', Message.content).op('@@')(
                        func.plainto_tsquery('simple', query)
                    )
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit * 3)  # Get more messages, then group by conversation
        )

        # Execute searches
        title_result = await self.db.execute(title_search)
        conversations_by_title = {c.id: c for c in title_result.scalars().all()}

        message_result = await self.db.execute(message_search)
        messages = list(message_result.scalars().all())

        # Group messages by conversation
        conversations_by_message = {}
        for msg in messages:
            if msg.conversation_id not in conversations_by_message:
                conversations_by_message[msg.conversation_id] = []
            conversations_by_message[msg.conversation_id].append(msg)

        # Load conversations for messages
        if conversations_by_message:
            conv_ids = list(conversations_by_message.keys())
            conv_query = select(Conversation).where(Conversation.id.in_(conv_ids))
            conv_result = await self.db.execute(conv_query)
            for conv in conv_result.scalars().all():
                if conv.id not in conversations_by_title:
                    conversations_by_title[conv.id] = conv

        # Combine results
        results = []
        for conv_id, conv in conversations_by_title.items():
            matched_messages = conversations_by_message.get(conv_id, [])
            results.append((conv, matched_messages))

        # Sort by relevance (conversations with message matches first)
        results.sort(key=lambda x: len(x[1]), reverse=True)

        return results[:limit]
