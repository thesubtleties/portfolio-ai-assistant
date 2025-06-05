from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.database import Conversation, Visitor
import redis.asyncio as redis
import json
import asyncio
import logging
import uuid


logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def get_or_create_conversation(
        self,
        visitor_id: str,
        conversation_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Get existing conversation or create new one (works for both REST and WebSocket).

        Args:
            visitor_id (str): Unique visitor ID
            conversation_id (Optional[str]): Existing conversation ID (from localStorage)
            connection_id (Optional[str]): WebSocket connection ID (None for REST)
            ai_model_used (Optional[str]): AI model used in conversation

        Returns:
            Conversation: Existing or newly created conversation
        """
        # If conversation_id provided, try cache first
        if conversation_id:
            try:
                cached_conv = await self.redis.hgetall(f"active_conv:{conversation_id}")
                if cached_conv and cached_conv.get("conversation_id"):
                    # Update cache with new activity
                    cache_update = {
                        "last_activity": datetime.now(timezone.utc).isoformat(),
                    }
                    # Only update connection_id if this is a WebSocket call
                    if connection_id:
                        cache_update["connection_id"] = connection_id

                    await self.redis.hset(
                        f"active_conv:{conversation_id}",
                        mapping=cache_update,
                    )

                    # build conversation object from cache
                    conversation = self._build_conversation_from_cache(
                        cached_conv, connection_id
                    )

                    # sync to DB but in background (only if WebSocket)
                    if connection_id:
                        asyncio.create_task(
                            self._sync_connection_to_db(
                                cached_conv["conversation_id"], connection_id
                            )
                        )

                    logger.info(f"Cache HIT for conversation {conversation_id}")
                    return conversation
            except Exception as e:
                logger.error(f"Cache FAIL for conversation {conversation_id}: {e}")

            # Cache miss, try to get conversation from DB
            try:
                conv_uuid = uuid.UUID(conversation_id)
                stmt = select(Conversation).where(Conversation.id == conv_uuid)
                result = await self.db.execute(stmt)
                existing_conversation = result.scalar_one_or_none()

                if existing_conversation and existing_conversation.visitor_id == uuid.UUID(visitor_id):
                    # Update connection_id if this is WebSocket
                    if connection_id:
                        if not existing_conversation.conversation_metadata:
                            existing_conversation.conversation_metadata = {}
                        existing_conversation.conversation_metadata["current_connection_id"] = connection_id
                    
                    existing_conversation.last_message_at = datetime.now(timezone.utc)
                    await self.db.commit()

                    # Cache the conversation
                    await self._cache_conversation(existing_conversation, conversation_id)
                    return existing_conversation
            except ValueError:
                # Invalid UUID format, continue to create new conversation
                pass

        # No existing conversation found, create new one
        return await self._create_new_conversation(
            visitor_id=visitor_id,
            connection_id=connection_id,
            ai_model_used=ai_model_used,
        )

    async def _create_new_conversation(
        self,
        visitor_id: str,
        connection_id: Optional[str] = None,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        now = datetime.now(timezone.utc)
        
        metadata = {}
        if connection_id:
            metadata["current_connection_id"] = connection_id

        conversation = Conversation(
            visitor_id=uuid.UUID(visitor_id),
            started_at=now,
            last_message_at=now,
            status="active_ai",
            ai_model_used=ai_model_used,
            conversation_metadata=metadata,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        # Cache the new conversation using its ID
        await self._cache_conversation(conversation, str(conversation.id))
        return conversation

    async def update_connection_on_disconnect(
        self,
        connection_id: str,
    ) -> bool:
        """Update connection status on disconnect but don't end conversation
        Args:
            db (AsyncSession): Database session for executing queries
            connection_id (str): Unique connection ID to update
        Returns:
            bool: True if updated successfully, False otherwise
        """
        stmt = select(Conversation).where(
            Conversation.conversation_metadata.op("->>")(
                "current_connection_id"
            )
            == connection_id,
            Conversation.status.in_(
                ["active_ai", "active_human", "escalation_pending"]
            ),
        )

        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            # Just mark as disconnected, don't end conversation
            if not conversation.conversation_metadata:
                conversation.conversation_metadata = {}
            conversation.conversation_metadata["connection_status"] = (
                "disconnected"
            )
            conversation.conversation_metadata["last_disconnect"] = (
                datetime.now(timezone.utc).isoformat()
            )
            await self.db.commit()
            return True
        return False

    async def _cache_conversation(
        self,
        conversation: Conversation,
        conversation_id: str,
    ) -> None:
        """Cache conversation in Redis for quick access"""

        await self.redis.hset(
            f"active_conv:{conversation_id}",
            mapping={
                "conversation_id": str(conversation.id),
                "visitor_id": str(conversation.visitor_id),
                "connection_id": conversation.conversation_metadata.get(
                    "current_connection_id"
                ),
                "status": conversation.status,
                "started_at": conversation.started_at.isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "last_message_at": conversation.last_message_at.isoformat(),
                "ai_model_used": conversation.ai_model_used or "",
                "conversation_metadata": json.dumps(
                    conversation.conversation_metadata or {}
                ),
            },
        )
        await self.redis.expire(
            f"active_conv:{conversation_id}", 3600  # Cache for 1 hour
        )

    def _build_conversation_from_cache(
        self,
        cached_conv: dict,
        new_connection_id: str,
    ) -> Conversation:
        """Build a Conversation object from cached data with updated connection ID"""
        return Conversation(
            id=uuid.UUID(cached_conv["conversation_id"]),
            visitor_id=uuid.UUID(cached_conv["visitor_id"]),
            started_at=datetime.fromisoformat(cached_conv["started_at"]),
            last_message_at=datetime.fromisoformat(
                cached_conv["last_message_at"]
            ),
            status=cached_conv["status"],
            conversation_metadata={
                "current_connection_id": new_connection_id,  # Update with new connection
            },
        )

    async def cleanup_old_conversations(
        self, hours_old: int = 24
    ) -> int:
        """Background task to cleanup old conversations"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)

        stmt = select(Conversation).where(
            Conversation.status.in_(
                ["active_ai", "active_human", "escalation_pending"]
            ),
            Conversation.last_message_at < cutoff_time,
        )

        result = await self.db.execute(stmt)
        old_conversations = result.scalars().all()

        for conv in old_conversations:
            conv.status = "ended"
            conv.ended_at = datetime.now(timezone.utc)
            conv.conversation_metadata = conv.conversation_metadata or {}
            conv.conversation_metadata["end_reason"] = "timeout_cleanup"

        await self.db.commit()
        return len(old_conversations)

    async def _sync_connection_to_db(
        self, conversation_id: str, connection_id: str
    ) -> None:
        """Update database with new connection ID in background"""
        try:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id
            )
            result = await self.db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation:
                # Update connection_id in metadata
                if not conversation.conversation_metadata:
                    conversation.conversation_metadata = {}
                conversation.conversation_metadata["current_connection_id"] = (
                    connection_id
                )
                conversation.last_message_at = datetime.now(timezone.utc)
                await self.db.commit()
                logger.info(
                    f"Synced connection {connection_id} to DB for conversation {conversation_id}"
                )
            else:
                logger.warning(
                    f"Conversation {conversation_id} not found for connection sync"
                )
        except Exception as e:
            logger.error(
                f"Failed to sync connection {connection_id} to DB: {e}"
            )
            # Don't re-raise - this is background task, shouldn't break main flow
