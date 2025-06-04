import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime, timezone

from app.services.visitor_service import VisitorService
from app.models.database import Visitor


class TestVisitorService:
    """Test visitor service functionality with TDD approach"""

    @pytest.mark.asyncio
    async def test_get_or_create_visitor_cache_hit(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should return visitor from cache when available"""
        # Arrange
        fingerprint = "test_fingerprint_123"
        visitor = sample_visitor(fingerprint_id=fingerprint)

        # Mock Redis cache hit
        mock_redis.hgetall.return_value = {
            "visitor_id": str(visitor.id),
            "fingerprint_id": fingerprint,
            "first_seen_at": visitor.first_seen_at.isoformat(),
            "last_seen_at": visitor.last_seen_at.isoformat(),
        }

        # Mock DB query for visitor (cache hit still validates with DB)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = visitor
        mock_db.execute.return_value = mock_result

        # Act
        result_visitor, created = await VisitorService.get_or_create_visitor(
            mock_db, mock_redis, fingerprint
        )

        # Assert
        assert result_visitor.id == visitor.id
        assert not created
        mock_redis.hgetall.assert_called_once_with(f"visitor:{fingerprint}")
        mock_redis.hset.assert_called_once()  # Updates last_seen_at
        mock_redis.expire.assert_called_with(
            f"visitor:{fingerprint}", 7 * 24 * 3600
        )

    @pytest.mark.asyncio
    async def test_get_or_create_visitor_cache_miss_existing(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should fetch from DB when cache misses but visitor exists"""
        # Arrange
        fingerprint = "test_fingerprint_456"
        visitor = sample_visitor(fingerprint_id=fingerprint)

        # Mock Redis cache miss
        mock_redis.hgetall.return_value = {}

        # Mock DB query returns existing visitor
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = visitor
        mock_db.execute.return_value = mock_result

        # Act
        result_visitor, created = await VisitorService.get_or_create_visitor(
            mock_db, mock_redis, fingerprint
        )

        # Assert
        assert result_visitor.id == visitor.id
        assert not created
        mock_db.commit.assert_called_once()  # Updates last_seen_at
        # Should cache the visitor after DB lookup
        assert mock_redis.hset.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_or_create_visitor_new(self, mock_db, mock_redis):
        """Should create new visitor when not found"""
        # Arrange
        fingerprint = "new_fingerprint_789"
        user_agent = "Mozilla/5.0 Test"
        ip_hash = "test_ip_hash"

        # Mock Redis cache miss
        mock_redis.hgetall.return_value = {}

        # Mock DB query returns None (no existing visitor)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock successful visitor creation
        new_visitor = Visitor(
            id=uuid.uuid4(),
            fingerprint_id=fingerprint,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            user_agent_raw=user_agent,
            ip_address_hash=ip_hash,
        )

        # Act
        result_visitor, created = await VisitorService.get_or_create_visitor(
            mock_db, mock_redis, fingerprint, user_agent, ip_hash
        )

        # Assert
        assert created is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_once()
        # Should cache the new visitor
        assert mock_redis.hset.call_count >= 1

    @pytest.mark.asyncio
    async def test_update_visitor_data_updates_cache(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should update both database and cache when updating visitor data"""
        # Arrange
        visitor = sample_visitor()
        profile_data = {"name": "John Doe", "company": "Test Corp"}

        # Act
        await VisitorService.update_visitor_data(
            visitor, profile_data, mock_db, mock_redis
        )

        # Assert
        assert visitor.profile_data == profile_data
        mock_db.commit.assert_called_once()
        # Should update cache
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_update_agent_notes_updates_cache(
        self, mock_db, mock_redis, sample_visitor
    ):
        """Should update both database and cache when updating agent notes"""
        # Arrange
        visitor = sample_visitor()
        notes = "User interested in React projects"

        # Act
        await VisitorService.update_agent_notes(
            visitor, notes, mock_db, mock_redis
        )

        # Assert
        assert notes in visitor.notes_by_agent
        mock_db.commit.assert_called_once()
        # Should update cache
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_cache_visitor_stores_correct_data(
        self, mock_redis, sample_visitor
    ):
        """Should cache visitor with correct data structure and TTL"""
        # Arrange
        visitor = sample_visitor(
            profile_data={"name": "Test User"}, notes_by_agent="Test notes"
        )

        # Act
        await VisitorService._cache_visitor(mock_redis, visitor)

        # Assert
        cache_key = f"visitor:{visitor.fingerprint_id}"
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == cache_key

        # Verify data structure
        mapping = call_args[1]["mapping"]
        assert mapping["visitor_id"] == str(visitor.id)
        assert mapping["fingerprint_id"] == visitor.fingerprint_id
        assert '"name": "Test User"' in mapping["profile_data"]

        # Verify TTL (7 days)
        mock_redis.expire.assert_called_once_with(cache_key, 7 * 24 * 3600)
