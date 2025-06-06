from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.database import Message, Conversation
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import redis.asyncio as redis
import json
import logging
import uuid


logger = logging.getLogger(__name__)


class MessageService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def save_message(
        self,
        conversation_id: str,
        sender_type: str,
        content: str,
        human_agent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Save a message to the conversation.
        Args:
            conversation_id (str): ID of the conversation to which the message belongs
            sender_type (str): Type of the sender ('visitor', 'ai', 'human_agent')
            content (str): Content of the message
            human_agent_id (Optional[str], optional): ID of the human agent if applicable. Defaults to None.
            metadata (Optional[dict], optional): Additional metadata for the message. Defaults to None.
        """

        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            human_agent_id=human_agent_id,
            message_metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(message)

        # Update conversation's last_message_at timestamp using SQLAlchemy 2.0+ style
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(message)

        # Cache the message
        await self._cache_message(message, conversation_id)

        return message

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Message]:
        """Get messages for a specific conversation.
        Args:
            conversation_id (str): ID of the conversation to fetch messages for
            limit (int, optional): Maximum number of messages to return. Defaults to 50.
        """

        # Try to get recent messages from cache first
        cached_messages = await self._get_cached_messages(
            conversation_id, limit
        )

        if cached_messages:
            logger.info(
                f"Cache HIT for conversation {conversation_id} messages"
            )
            return cached_messages

        # Cache miss, get from database
        logger.info(
            f"Cache MISS for conversation {conversation_id} messages, fetching from DB"
        )

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # Cache the messages for future requests
        if messages:
            await self._cache_messages(messages, conversation_id)

        return messages

    async def _cache_message(
        self,
        message: Message,
        conversation_id: str,
    ) -> None:
        """Cache a single message and add to conversation's message list"""

        # Cache individual message
        message_key = f"message:{message.id}"
        message_data = {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_type": message.sender_type,
            "content": message.content,
            "human_agent_id": message.human_agent_id or "",
            "message_metadata": json.dumps(message.message_metadata or {}),
            "timestamp": message.timestamp.isoformat(),
        }

        await self.redis.hset(message_key, mapping=message_data)
        await self.redis.expire(
            message_key, 3600
        )  # 1 hour TTL for individual messages

        # Add to conversation's message list (sorted set by timestamp)
        conv_messages_key = f"conv_messages:{conversation_id}"
        score = message.timestamp.timestamp()
        await self.redis.zadd(conv_messages_key, {str(message.id): score})

        # Keep only recent messages in the sorted set (last 100)
        await self.redis.zremrangebyrank(conv_messages_key, 0, -101)
        await self.redis.expire(conv_messages_key, 3600)  # 1 hour TTL

    async def _cache_messages(
        self,
        messages: List[Message],
        conversation_id: str,
    ) -> None:
        """Cache multiple messages for a conversation"""

        conv_messages_key = f"conv_messages:{conversation_id}"

        # Clear existing cached messages for this conversation
        await self.redis.delete(conv_messages_key)

        # Cache each message
        for message in messages:
            await self._cache_message(message, conversation_id)

    async def _get_cached_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> Optional[List[Message]]:
        """Get cached messages for a conversation"""

        try:
            conv_messages_key = f"conv_messages:{conversation_id}"

            # Get message IDs from sorted set (ordered by timestamp)
            message_ids = await self.redis.zrange(
                conv_messages_key, 0, limit - 1
            )

            if not message_ids:
                return None

            # Get message data for each ID
            messages = []
            for message_id in message_ids:
                message_key = f"message:{message_id}"
                message_data = await self.redis.hgetall(message_key)

                if message_data:
                    # Reconstruct Message object from cached data
                    message = Message(
                        id=uuid.UUID(message_data["id"]),
                        conversation_id=uuid.UUID(
                            message_data["conversation_id"]
                        ),
                        sender_type=message_data["sender_type"],
                        content=message_data["content"],
                        human_agent_id=message_data["human_agent_id"] or None,
                        message_metadata=json.loads(
                            message_data["message_metadata"]
                        ),
                        timestamp=datetime.fromisoformat(
                            message_data["timestamp"]
                        ),
                    )
                    messages.append(message)

            return messages if messages else None

        except Exception as e:
            logger.error(
                f"Error getting cached messages for conversation {conversation_id}: {e}"
            )
            return None

    async def get_recent_messages(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Message]:
        """Get recent messages across all conversations"""

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(Message)
            .where(Message.timestamp > cutoff_time)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()
