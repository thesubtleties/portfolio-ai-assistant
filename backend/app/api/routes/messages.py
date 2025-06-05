"""Message handling endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.services.message_service import MessageService
import redis.asyncio as redis
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    conversation_id: str = Field(
        ...,
        description="ID of the conversation to send message to",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    content: str = Field(
        ...,
        description="Message content",
        examples=["Hello! Can you tell me about Steven's experience with React?"]
    )


class MessageResponse(BaseModel):
    """Response model for a message."""

    id: str = Field(
        ...,
        description="Unique message identifier",
        examples=["789e0123-e45f-67g8-h901-234567890abc"]
    )
    conversation_id: str = Field(
        ...,
        description="ID of the conversation this message belongs to",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    content: str = Field(
        ...,
        description="Message content",
        examples=["Hello! How can I help you today?"]
    )
    sender_type: str = Field(
        ...,
        description="Who sent the message (visitor, ai, human_agent)",
        examples=["ai"]
    )
    timestamp: datetime = Field(
        ...,
        description="When the message was sent",
        examples=["2024-01-15T10:35:00Z"]
    )


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    user_message: MessageResponse = Field(
        ...,
        description="The user's message that was sent"
    )
    ai_response: MessageResponse = Field(
        ...,
        description="The AI's response to the user's message"
    )


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest, 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> SendMessageResponse:
    """
    Send a message in a conversation.

    This endpoint:
    1. Creates the user's message
    2. Generates an AI response (for now, just echo)
    3. Returns both messages
    """
    message_service = MessageService(db, redis_client)

    try:
        conv_id = uuid.UUID(request.conversation_id)

        # Note: We'll validate conversation exists when saving the message
        # The message service will handle updating conversation timestamps

        # Create user message
        user_message = await message_service.save_message(
            conversation_id=str(conv_id),
            sender_type="visitor",
            content=request.content,
        )

        # For now, just echo back (later this will call AI)
        ai_content = f"Echo: {request.content}"

        # Create AI response
        ai_message = await message_service.save_message(
            conversation_id=str(conv_id),
            sender_type="ai",
            content=ai_content,
            metadata={"model": "echo", "version": "1.0"},
        )

        # Conversation timestamps are automatically updated by message service

        return SendMessageResponse(
            user_message=MessageResponse(
                id=str(user_message.id),
                conversation_id=str(user_message.conversation_id),
                content=user_message.content,
                sender_type=user_message.sender_type,
                timestamp=user_message.timestamp,
            ),
            ai_response=MessageResponse(
                id=str(ai_message.id),
                conversation_id=str(ai_message.conversation_id),
                content=ai_message.content,
                sender_type=ai_message.sender_type,
                timestamp=ai_message.timestamp,
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid conversation_id: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send message: {str(e)}"
        )
