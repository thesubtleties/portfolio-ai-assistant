import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import uuid
import json

from app.services.conversation_service import ConversationService
from app.models.database import Conversation, Message, Visitor


class TestConversationService:
    """Test conversation service functionality"""

    @pytest.mark.asyncio
    async def test_get_or_create_current_conversation_cache_hit(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should return conversation from cache when available"""
        # Arrange
        visitor = sample_visitor()
        session_id = "test_session_123"
        connection_id = "test_connection_123"
        conversation_id = uuid.uuid4()
        cached_conv = {
            "conversation_id": str(conversation_id),
            "visitor_id": str(visitor.id),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "status": "active_ai",
            "connection_id": connection_id,
            "ai_model_used": "gpt-3.5-turbo",
            "session_id": session_id,
        }

        mock_redis.hgetall.return_value = cached_conv

        # Act
        conversation = (
            await ConversationService.get_or_create_current_conversation(
                mock_db, mock_redis, str(visitor.id), connection_id, session_id
            )
        )

        # Assert
        assert str(conversation.id) == cached_conv["conversation_id"]
        assert str(conversation.visitor_id) == cached_conv["visitor_id"]
        assert conversation.status == cached_conv["status"]
        assert conversation.conversation_metadata["session_id"] == session_id
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == connection_id
        )

        # Verify cache was used, not database
        mock_redis.hgetall.assert_called_once_with(f"active_conv:{session_id}")
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_current_conversation_cache_miss(
        self, mock_db, mock_redis, sample_visitor, sample_conversation
    ):
        """Should fallback to DB when cache misses and update to new connection_id"""
        # Arrange
        visitor = sample_visitor()
        session_id = "test_session_456"
        connection_id = "test_connection_456"
        existing_conversation = sample_conversation(
            visitor_id=visitor.id,
            status="active_ai",
            conversation_metadata={
                "session_id": session_id,
                "current_connection_id": "old_connection_id",
            },
        )

        # Mock Redis cache miss
        mock_redis.hgetall.return_value = {}

        # Mock DB query to return conversation as found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_conversation
        mock_db.execute.return_value = (
            mock_result  # Mock DB returns existing conversation
        )
        # Act
        conversation = (
            await ConversationService.get_or_create_current_conversation(
                mock_db, mock_redis, str(visitor.id), connection_id, session_id
            )
        )

        # Assert
        assert conversation == existing_conversation
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == connection_id
        )
        assert conversation.conversation_metadata["session_id"] == session_id

        # Verify cache miss
        mock_redis.hgetall.assert_called_once_with(f"active_conv:{session_id}")
        mock_db.execute.assert_called_once()

        # Verify conversation was updated in DB
        mock_db.commit.assert_called_once()

        # Verify cache was updated
        mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_get_or_create_current_conversation_cache_miss_no_existing_creates_new(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should create new conversation when cache misses and no existing conversation"""
        # Arrange
        visitor = sample_visitor()
        session_id = "test_session_789"
        connection_id = "test_connection_789"
        ai_model = "gpt-4"

        # Mock Redis cache miss
        mock_redis.hgetall.return_value = {}

        # Mock DB query to return no existing conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        conversation = (
            await ConversationService.get_or_create_current_conversation(
                mock_db,
                mock_redis,
                str(visitor.id),
                connection_id,
                session_id,
                ai_model,
            )
        )

        # Assert
        assert str(conversation.visitor_id) == str(visitor.id)
        assert conversation.status == "active_ai"
        assert conversation.ai_model_used == ai_model
        assert conversation.conversation_metadata["session_id"] == session_id
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == connection_id
        )

        # Verify cache miss and DB query
        mock_redis.hgetall.assert_called_once()
        mock_db.execute.assert_called_once()

        # Verify new conversation was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_once()

        # Verify cache was updated
        mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_get_or_create_current_conversation_cache_error_fallback(
        self, mock_db, mock_redis, sample_visitor, sample_conversation
    ):
        """Should fallback to DB when Redis cache throws exception"""
        # Arrange
        visitor = sample_visitor()
        session_id = "test_session_error"
        connection_id = "test_connection_error"
        existing_conversation = sample_conversation(
            visitor_id=visitor.id,
            conversation_metadata={"session_id": session_id},
        )

        # Mock Redis error
        mock_redis.hgetall.side_effect = Exception("Redis connection error")

        # Mock DB query to return existing conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_conversation
        mock_db.execute.return_value = mock_result

        # Act
        conversation = (
            await ConversationService.get_or_create_current_conversation(
                mock_db, mock_redis, str(visitor.id), connection_id, session_id
            )
        )

        # Assert
        assert conversation == existing_conversation
        # Should fallback to database despite Redis error
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should create new conversation with proper defaults"""
        # Arrange
        visitor = sample_visitor()
        session_id = "new_session_123"
        connection_id = "new_connection_123"
        ai_model = "gpt-3.5-turbo"

        # Act
        conversation = await ConversationService.create_conversation(
            mock_db,
            mock_redis,
            str(visitor.id),
            connection_id,
            session_id,
            ai_model,
        )

        # Assert
        assert str(conversation.visitor_id) == str(visitor.id)
        assert conversation.status == "active_ai"
        assert conversation.ai_model_used == ai_model
        assert conversation.conversation_metadata["session_id"] == session_id
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == connection_id
        )

        # Verify database operations
        mock_db.add.assert_called_once_with(conversation)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(conversation)

        # Verify caching
        mock_redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_update_connection_on_disconnect_success(
        self, mock_db, sample_conversation
    ):
        """Should update conversation metadata on disconnect"""
        # Arrange
        connection_id = "disconnecting_connection_123"
        conversation = sample_conversation(
            conversation_metadata={"current_connection_id": connection_id}
        )

        # Mock DB query to find conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        mock_db.execute.return_value = mock_result

        # Act
        result = await ConversationService.update_connection_on_disconnect(
            mock_db, connection_id
        )

        # Assert
        assert result is True
        assert (
            conversation.conversation_metadata["connection_status"]
            == "disconnected"
        )
        assert "last_disconnect" in conversation.conversation_metadata
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_connection_on_disconnect_not_found(self, mock_db):
        """Should return False when conversation not found"""
        # Arrange
        connection_id = "nonexistent_connection"

        # Mock DB query to return no conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await ConversationService.update_connection_on_disconnect(
            mock_db, connection_id
        )

        # Assert
        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(
        self, mock_db, sample_conversation
    ):
        """Should mark old conversations as ended"""
        # Arrange
        old_conversation1 = sample_conversation(status="active_ai")
        old_conversation2 = sample_conversation(status="active_human")

        # Mock DB query to return old conversations
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            old_conversation1,
            old_conversation2,
        ]
        mock_db.execute.return_value = mock_result

        # Act
        count = await ConversationService.cleanup_old_conversations(
            mock_db, hours_old=24
        )

        # Assert
        assert count == 2
        assert old_conversation1.status == "ended"
        assert old_conversation2.status == "ended"
        assert old_conversation1.ended_at is not None
        assert old_conversation2.ended_at is not None
        assert (
            old_conversation1.conversation_metadata["end_reason"]
            == "timeout_cleanup"
        )
        assert (
            old_conversation2.conversation_metadata["end_reason"]
            == "timeout_cleanup"
        )
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_connection_to_db_success(
        self, mock_db, sample_conversation
    ):
        """Should update conversation connection_id in background"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        new_connection_id = "new_bg_connection_123"
        conversation = sample_conversation(
            id=conversation_id,
            conversation_metadata={"current_connection_id": "old_connection"},
        )

        # Mock DB query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        mock_db.execute.return_value = mock_result

        # Act
        await ConversationService._sync_connection_to_db(
            mock_db, conversation_id, new_connection_id
        )

        # Assert
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == new_connection_id
        )
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_connection_to_db_not_found(self, mock_db):
        """Should handle conversation not found gracefully"""
        # Arrange
        conversation_id = str(uuid.uuid4())
        new_connection_id = "connection_123"

        # Mock DB query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act (should not raise exception)
        await ConversationService._sync_connection_to_db(
            mock_db, conversation_id, new_connection_id
        )

        # Assert
        mock_db.commit.assert_not_called()

    def test_build_conversation_from_cache(self):
        """Should properly reconstruct Conversation object from cache data"""
        # Arrange
        conversation_id = uuid.uuid4()
        visitor_id = uuid.uuid4()
        new_connection_id = "test_connection_build"
        cached_data = {
            "conversation_id": str(conversation_id),
            "visitor_id": str(visitor_id),
            "started_at": "2023-01-01T10:00:00+00:00",
            "last_message_at": "2023-01-01T10:30:00+00:00",
            "status": "active_ai",
            "session_id": "cached_session_123",
        }

        # Act
        conversation = ConversationService._build_conversation_from_cache(
            cached_data, new_connection_id
        )

        # Assert
        assert conversation.id == conversation_id
        assert conversation.visitor_id == visitor_id
        assert conversation.status == "active_ai"
        assert (
            conversation.conversation_metadata["current_connection_id"]
            == new_connection_id
        )
        assert (
            conversation.conversation_metadata["session_id"]
            == "cached_session_123"
        )

    @pytest.mark.asyncio
    async def test_cache_conversation(self, mock_redis, sample_conversation):
        """Should cache conversation data properly"""
        # Arrange
        session_id = "cache_test_session"
        conversation = sample_conversation(
            conversation_metadata={
                "current_connection_id": "test_conn",
                "session_id": session_id,
            }
        )

        # Act
        await ConversationService._cache_conversation(
            mock_redis, conversation, session_id
        )

        # Assert
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once_with(
            f"active_conv:{session_id}", 3600
        )
