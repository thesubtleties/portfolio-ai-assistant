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
    @staticmethod
    async def get_or_create_current_conversation(
        db: AsyncSession,
        redis_client: redis.Redis,
        visitor_id: str,
        connection_id: str,
        session_id: str,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Get active conversation for this browser session only, or create a new one if none exists.
        Args:
            db (AsyncSession): Database session for executing queries
            visitor_id (str): Unique visitor ID
            connection_id (str): Unique connection ID for the current session
            session_id (str): Unique session ID for the current session
            ai_model_used (Optional[str], optional): AI model used in the conversation. Defaults to None.
        """
        try:
            cached_conv = await redis_client.hgetall(
                f"active_conv:{session_id}"
            )
            if cached_conv and cached_conv.get("conversation_id"):

                # update connection in Redis cache
                await redis_client.hset(
                    f"active_conv:{session_id}",
                    mapping={
                        "connection_id": connection_id,
                        "last_activity": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    },
                )

                # build conversation object from cache
                conversation = (
                    ConversationService._build_conversation_from_cache(
                        cached_conv, connection_id
                    )
                )
                # sync to DB but in background
                asyncio.create_task(
                    ConversationService._sync_connection_to_db(
                        db, cached_conv["conversation_id"], connection_id
                    )
                )

                logger.info(f"Cache HIT for session {session_id}")
                return conversation
        except Exception as e:
            logger.error(f"Cache FAIL for session {session_id}: {e}")

        logger.info(f"Falling back to DB for session {session_id}")

        stmt = (
            select(Conversation)
            .where(
                Conversation.status.in_(
                    ["active_ai", "active_human", "escalation_pending"]
                ),
                Conversation.conversation_metadata.op("->>")("session_id")
                == session_id,
            )
            .order_by(Conversation.last_message_at.desc())
        )

        result = await db.execute(stmt)
        active_conversation = result.scalar_one_or_none()

        if active_conversation:
            # Update connection_id for this websocket connection
            active_conversation.conversation_metadata[
                "current_connection_id"
            ] = connection_id
            active_conversation.last_message_at = datetime.now(timezone.utc)
            await db.commit()  # async commit

            await ConversationService._cache_conversation(
                redis_client, active_conversation, session_id
            )
            return active_conversation

        return await ConversationService.create_conversation(
            db=db,
            redis_client=redis_client,
            visitor_id=visitor_id,
            connection_id=connection_id,
            session_id=session_id,
            ai_model_used=ai_model_used,
        )

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        redis_client: redis.Redis,
        visitor_id: str,
        connection_id: str,
        session_id: str,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        now = datetime.now(timezone.utc)

        conversation = Conversation(
            visitor_id=visitor_id,
            started_at=now,
            last_message_at=now,
            status="active_ai",
            ai_model_used=ai_model_used,
            conversation_metadata={
                "current_connection_id": connection_id,
                "session_id": session_id,
            },
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        await ConversationService._cache_conversation(
            redis_client, conversation, session_id
        )
        return conversation

    @staticmethod
    async def update_connection_on_disconnect(
        db: AsyncSession,
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

        result = await db.execute(stmt)
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
            await db.commit()
            return True
        return False

    @staticmethod
    async def _cache_conversation(
        redis_client: redis.Redis,
        conversation: Conversation,
        session_id: str,
    ) -> None:
        """Cache conversation in Redis for quick access"""

        await redis_client.hset(
            f"active_conv:{session_id}",
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
                "session_id": session_id,
                "conversation_metadata": json.dumps(
                    conversation.conversation_metadata or {}
                ),
            },
        )
        await redis_client.expire(
            f"active_conv:{session_id}", 3600  # Cache for 1 hour
        )

    @staticmethod
    def _build_conversation_from_cache(
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
                "session_id": cached_conv.get("session_id"),  # Keep from cache
            },
        )

    @staticmethod
    async def cleanup_old_conversations(
        db: AsyncSession, hours_old: int = 24
    ) -> int:
        """Background task to cleanup old conversations"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)

        stmt = select(Conversation).where(
            Conversation.status.in_(
                ["active_ai", "active_human", "escalation_pending"]
            ),
            Conversation.last_message_at < cutoff_time,
        )

        result = await db.execute(stmt)
        old_conversations = result.scalars().all()

        for conv in old_conversations:
            conv.status = "ended"
            conv.ended_at = datetime.now(timezone.utc)
            conv.conversation_metadata = conv.conversation_metadata or {}
            conv.conversation_metadata["end_reason"] = "timeout_cleanup"

        await db.commit()
        return len(old_conversations)

    @staticmethod
    async def _sync_connection_to_db(
        db: AsyncSession, conversation_id: str, connection_id: str
    ) -> None:
        """Update database with new connection ID in background"""
        try:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation:
                # Update connection_id in metadata
                if not conversation.conversation_metadata:
                    conversation.conversation_metadata = {}
                conversation.conversation_metadata["current_connection_id"] = (
                    connection_id
                )
                conversation.last_message_at = datetime.now(timezone.utc)
                await db.commit()
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
