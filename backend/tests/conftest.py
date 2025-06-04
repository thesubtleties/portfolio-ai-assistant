import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import uuid
from datetime import datetime, timezone

from app.models.database import Visitor, Conversation, Message, HumanAgent


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock database session"""
    mock = MagicMock(spec=AsyncSession)
    # Common async methods
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.refresh = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = MagicMock(spec=redis.Redis)
    # Common Redis methods as async
    mock.hgetall = AsyncMock(return_value={})
    mock.hset = AsyncMock()
    mock.expire = AsyncMock()
    mock.delete = AsyncMock()
    mock.zadd = AsyncMock()
    mock.zrange = AsyncMock()
    mock.zremrangebyrank = AsyncMock()
    return mock


@pytest.fixture
def sample_visitor():
    """Factory for test visitors"""

    def _make_visitor(**kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "fingerprint_id": f"test_fp_{uuid.uuid4().hex[:8]}",
            "first_seen_at": datetime.now(timezone.utc),
            "last_seen_at": datetime.now(timezone.utc),
            "user_agent_raw": "Mozilla/5.0 Test Browser",
            "ip_address_hash": "hashed_ip_123",
            "profile_data": None,
            "notes_by_agent": None,
        }
        defaults.update(kwargs)
        visitor = Visitor(**defaults)
        return visitor

    return _make_visitor


@pytest.fixture
def sample_conversation():
    """Factory for test conversations"""

    def _make_conversation(**kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "visitor_id": uuid.uuid4(),
            "started_at": datetime.now(timezone.utc),
            "ended_at": None,
            "last_message_at": datetime.now(timezone.utc),
            "status": "active_ai",
            "assigned_human_agent_id": None,
            "ai_model_used": None,
            "conversation_metadata": None,
        }
        defaults.update(kwargs)
        conversation = Conversation(**defaults)
        return conversation

    return _make_conversation


@pytest.fixture
def sample_message():
    """Factory for test messages"""

    def _make_message(**kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "conversation_id": uuid.uuid4(),
            "sender_type": "visitor",  # visitor, ai, human_agent
            "content": "Test message content",
            "timestamp": datetime.now(timezone.utc),
            "human_agent_id": None,
            "message_metadata": None,
        }
        defaults.update(kwargs)
        message = Message(**defaults)
        return message

    return _make_message


@pytest.fixture
def sample_human_agent():
    """Factory for test human agents"""

    def _make_human_agent(**kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "username": "test_agent",
            "display_name": "Test Agent",
            "email": "agent@test.com",
            "created_at": datetime.now(timezone.utc),
            "last_login_at": None,
        }
        defaults.update(kwargs)
        agent = HumanAgent(**defaults)
        return agent

    return _make_human_agent
