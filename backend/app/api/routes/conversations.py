"""Conversation management endpoints."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
import redis.asyncio as redis
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    """Request to start or continue a conversation."""

    visitor_id: str = Field(
        ...,
        description="Unique visitor identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID to continue (null for new conversation)",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )


class ConversationResponse(BaseModel):
    """Response model for conversation."""

    id: str = Field(
        ...,
        description="Unique conversation identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    visitor_id: str = Field(
        ...,
        description="Visitor who owns this conversation",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    started_at: datetime = Field(
        ...,
        description="When the conversation was started",
        examples=["2024-01-15T10:30:00Z"],
    )
    last_message_at: datetime = Field(
        ...,
        description="When the last message was sent",
        examples=["2024-01-15T10:35:00Z"],
    )
    status: str = Field(
        ..., description="Current conversation status", examples=["active_ai"]
    )
    message_count: int = Field(
        0, description="Number of messages in this conversation", examples=[5]
    )


class MessageResponse(BaseModel):
    """Response model for message."""

    id: str = Field(
        ...,
        description="Unique message identifier",
        examples=["789e0123-e45f-67g8-h901-234567890abc"],
    )
    content: str = Field(
        ...,
        description="Message content",
        examples=["Hello! How can I help you today?"],
    )
    sender_type: str = Field(
        ..., description="Who sent the message", examples=["ai"]
    )
    timestamp: datetime = Field(
        ...,
        description="When the message was sent",
        examples=["2024-01-15T10:35:00Z"],
    )


@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> ConversationResponse:
    """
    Start a new conversation or continue existing one.

    Uses the new unified get_or_create_conversation method.
    """
    conversation_service = ConversationService(db, redis_client)

    try:
        # Use the new unified method
        conversation = await conversation_service.get_or_create_conversation(
            visitor_id=request.visitor_id,
            conversation_id=request.conversation_id,
            ai_model_used=settings.openai_model,
        )

        # Get message count (simplified for now)
        message_count = (
            len(conversation.messages)
            if hasattr(conversation, "messages") and conversation.messages
            else 0
        )

        return ConversationResponse(
            id=str(conversation.id),
            visitor_id=str(conversation.visitor_id),
            started_at=conversation.started_at,
            last_message_at=conversation.last_message_at,
            status=conversation.status,
            message_count=message_count,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid visitor_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start conversation: {str(e)}"
        )


@router.get(
    "/{conversation_id}/messages", response_model=List[MessageResponse]
)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> List[MessageResponse]:
    """
    Get messages for a conversation.

    Returns messages ordered by timestamp (newest first).
    """
    message_service = MessageService(db, redis_client)

    try:
        conv_id = uuid.UUID(conversation_id)
        messages = await message_service.get_conversation_messages(
            conversation_id=str(conv_id), limit=limit
        )

        return [
            MessageResponse(
                id=str(msg.id),
                content=msg.content,
                sender_type=msg.sender_type,
                timestamp=msg.timestamp,
            )
            for msg in messages
        ]

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid conversation_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get messages: {str(e)}"
        )
