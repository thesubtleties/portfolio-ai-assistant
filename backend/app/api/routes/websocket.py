"""WebSocket endpoints for real-time messaging."""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.websocket_manager import manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    visitor_id: str = Query(..., description="Unique visitor identifier"),
    conversation_id: Optional[str] = Query(None, description="Existing conversation ID to continue"),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    WebSocket endpoint for real-time chat.
    
    Query Parameters:
    - visitor_id: Required. Browser fingerprint or unique visitor ID
    - conversation_id: Optional. Existing conversation to continue
    
    Message Format (Client -> Server):
    {
        "type": "user_message",
        "content": "Hello, how can you help me?"
    }
    
    {
        "type": "heartbeat"
    }
    
    Message Format (Server -> Client):
    {
        "type": "message_received",
        "message": {
            "id": "uuid",
            "content": "user message",
            "sender_type": "user",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
    
    {
        "type": "ai_response", 
        "message": {
            "id": "uuid",
            "content": "AI response",
            "sender_type": "ai",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
    
    {
        "type": "error",
        "error": "Error message"
    }
    
    {
        "type": "heartbeat_ack",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    
    connection_id = None
    try:
        # Connect and get conversation
        connection_id, active_conversation_id = await manager.connect(
            websocket=websocket,
            visitor_id=visitor_id,
            conversation_id=conversation_id,
            db=db,
            redis_client=redis_client,
        )
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Handle messages
        await manager.handle_message(
            websocket=websocket,
            connection_id=connection_id,
            db=db,
            redis_client=redis_client,
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if connection_id:
            await manager.disconnect(connection_id, db, redis_client)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "active_connections": manager.get_active_connections_count(),
        "active_conversations": len(manager.conversation_connections),
    }