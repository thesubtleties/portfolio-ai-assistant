import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import uuid
import json

from app.services.message_service import MessageService
from app.models.database import Message, Conversation


class TestMessageService:
    """Test cases for MessageService covering all three sender types"""

    @pytest.mark.asyncio
    async def test_save_message_from_visitor(
        self, mock_db, mock_redis, sample_message, sample_conversation
    ):
        """Test saving a message from a visitor"""
        # Arrange
        conversation = sample_conversation()
        message = sample_message(
            conversation_id=conversation.id,
            sender_type="visitor",
            content="Hello, I need help",
        )

        # Mock the conversation query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.save_message(
            db=mock_db,
            redis_client=mock_redis,
            conversation_id=str(conversation.id),
            sender_type="visitor",
            content="Hello, I need help",
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify Redis caching was called
        mock_redis.hset.assert_called()
        mock_redis.zadd.assert_called()

        # Verify conversation timestamp was updated
        assert conversation.last_message_at is not None

    @pytest.mark.asyncio
    async def test_save_message_from_ai_assistant(
        self, mock_db, mock_redis, sample_conversation
    ):
        """Test saving a message from AI assistant"""
        # Arrange
        conversation = sample_conversation()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.save_message(
            db=mock_db,
            redis_client=mock_redis,
            conversation_id=str(conversation.id),
            sender_type="ai",
            content="I can help you with that!",
            metadata={"model": "gpt-4", "tokens": 50},
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the message was created with correct sender type
        added_message = mock_db.add.call_args[0][0]
        assert added_message.sender_type == "ai"
        assert added_message.message_metadata == {
            "model": "gpt-4",
            "tokens": 50,
        }

    @pytest.mark.asyncio
    async def test_save_message_from_human_agent(
        self, mock_db, mock_redis, sample_conversation, sample_human_agent
    ):
        """Test saving a message from human agent"""
        # Arrange
        conversation = sample_conversation()
        agent = sample_human_agent()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.save_message(
            db=mock_db,
            redis_client=mock_redis,
            conversation_id=str(conversation.id),
            sender_type="human_agent",
            content="Let me escalate this to our team",
            human_agent_id=str(agent.id),
        )

        # Assert
        added_message = mock_db.add.call_args[0][0]
        assert added_message.sender_type == "human_agent"
        assert added_message.human_agent_id == str(agent.id)

    @pytest.mark.asyncio
    async def test_get_conversation_messages_cache_hit(
        self, mock_db, mock_redis, sample_message
    ):
        """Test getting messages when cache hit occurs"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        cached_messages = [
            sample_message(
                conversation_id=conversation_id, sender_type="visitor"
            ),
            sample_message(conversation_id=conversation_id, sender_type="ai"),
        ]

        # Mock Redis to return message IDs
        mock_redis.zrange.return_value = [
            str(msg.id) for msg in cached_messages
        ]

        # Mock Redis to return message data
        for msg in cached_messages:
            mock_redis.hgetall.return_value = {
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "sender_type": msg.sender_type,
                "content": msg.content,
                "human_agent_id": "",
                "message_metadata": "{}",
                "timestamp": msg.timestamp.isoformat(),
            }

        # Act
        with patch.object(
            MessageService,
            "_get_cached_messages",
            return_value=cached_messages,
        ):
            result = await MessageService.get_conversation_messages(
                db=mock_db,
                redis_client=mock_redis,
                conversation_id=conversation_id,
            )

        # Assert
        assert len(result) == 2
        assert result[0].sender_type == "visitor"
        assert result[1].sender_type == "ai"

        # Database should not be queried on cache hit
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_conversation_messages_cache_miss(
        self, mock_db, mock_redis, sample_message
    ):
        """Test getting messages when cache miss occurs"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        db_messages = [
            sample_message(
                conversation_id=conversation_id, sender_type="visitor"
            ),
            sample_message(conversation_id=conversation_id, sender_type="ai"),
            sample_message(
                conversation_id=conversation_id, sender_type="human_agent"
            ),
        ]

        # Mock cache miss
        mock_redis.zrange.return_value = []

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = db_messages
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.get_conversation_messages(
            db=mock_db,
            redis_client=mock_redis,
            conversation_id=conversation_id,
        )

        # Assert
        assert len(result) == 3
        assert result[0].sender_type == "visitor"
        assert result[1].sender_type == "ai"
        assert result[2].sender_type == "human_agent"

        # Verify database was queried
        mock_db.execute.assert_called_once()

        # Verify messages were cached
        assert mock_redis.hset.call_count >= 3  # One for each message
        assert mock_redis.zadd.call_count >= 3

    @pytest.mark.asyncio
    async def test_cache_message_with_metadata(
        self, mock_redis, sample_message
    ):
        """Test caching a message with metadata"""
        # Arrange
        message = sample_message(
            message_metadata={"intent": "support", "urgency": "high"}
        )
        conversation_id = str(message.conversation_id)

        # Act
        await MessageService._cache_message(
            mock_redis, message, conversation_id
        )

        # Assert
        # Verify message data was cached correctly
        call_args = mock_redis.hset.call_args
        cached_data = call_args[1]["mapping"]

        assert cached_data["id"] == str(message.id)
        assert cached_data["sender_type"] == message.sender_type
        assert json.loads(cached_data["message_metadata"]) == {
            "intent": "support",
            "urgency": "high",
        }

        # Verify TTL was set
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, mock_db, sample_message):
        """Test getting recent messages across all conversations"""
        # Arrange
        recent_messages = [
            sample_message(sender_type="visitor"),
            sample_message(sender_type="ai"),
            sample_message(sender_type="human_agent"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = recent_messages
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.get_recent_messages(
            db=mock_db, hours=24, limit=100
        )

        # Assert
        assert len(result) == 3
        assert any(msg.sender_type == "visitor" for msg in result)
        assert any(msg.sender_type == "ai" for msg in result)
        assert any(msg.sender_type == "human_agent" for msg in result)

    @pytest.mark.asyncio
    async def test_cache_messages_batch(self, mock_redis, sample_message):
        """Test caching multiple messages at once"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        messages = [
            sample_message(
                conversation_id=conversation_id, sender_type="visitor"
            ),
            sample_message(conversation_id=conversation_id, sender_type="ai"),
            sample_message(
                conversation_id=conversation_id, sender_type="visitor"
            ),
        ]

        # Act
        await MessageService._cache_messages(
            mock_redis, messages, conversation_id
        )

        # Assert
        # Verify conversation messages key was cleared first
        mock_redis.delete.assert_called_once_with(
            f"conv_messages:{conversation_id}"
        )

        # Verify each message was cached
        assert mock_redis.hset.call_count == 3
        assert mock_redis.zadd.call_count == 3

    @pytest.mark.asyncio
    async def test_conversation_message_limit_in_cache(
        self, mock_redis, sample_message
    ):
        """Test that cache keeps only recent 100 messages per conversation"""
        # Arrange
        message = sample_message()
        conversation_id = str(message.conversation_id)

        # Act
        await MessageService._cache_message(
            mock_redis, message, conversation_id
        )

        # Assert
        # Verify old messages are removed (keeping only last 100)
        mock_redis.zremrangebyrank.assert_called_with(
            f"conv_messages:{conversation_id}", 0, -101
        )

    @pytest.mark.asyncio
    async def test_get_cached_messages_error_handling(
        self, mock_redis, caplog
    ):
        """Test error handling in cache retrieval"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        mock_redis.zrange.side_effect = Exception("Redis connection error")

        # Act
        result = await MessageService._get_cached_messages(
            mock_redis, conversation_id
        )

        # Assert
        assert result is None
        assert "Error getting cached messages" in caplog.text

    @pytest.mark.asyncio
    async def test_message_ordering_preserved(
        self, mock_db, mock_redis, sample_message
    ):
        """Test that message ordering is preserved by timestamp"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        base_time = datetime.now(timezone.utc)

        messages = [
            sample_message(
                conversation_id=conversation_id,
                timestamp=base_time - timedelta(minutes=2),
                content="First message",
            ),
            sample_message(
                conversation_id=conversation_id,
                timestamp=base_time - timedelta(minutes=1),
                content="Second message",
            ),
            sample_message(
                conversation_id=conversation_id,
                timestamp=base_time,
                content="Third message",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result

        # Act
        result = await MessageService.get_conversation_messages(
            db=mock_db,
            redis_client=mock_redis,
            conversation_id=conversation_id,
        )

        # Assert
        assert result[0].content == "First message"
        assert result[1].content == "Second message"
        assert result[2].content == "Third message"
