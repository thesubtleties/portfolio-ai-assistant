"""WebSocket connection manager for real-time messaging."""

import json
import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
import logging
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Connection to conversation mapping: {connection_id: conversation_id}
        self.connection_conversations: Dict[str, str] = {}
        # Conversation to connections mapping: {conversation_id: Set[connection_id]}
        self.conversation_connections: Dict[str, Set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        visitor_id: str,
        conversation_id: Optional[str],
        db: AsyncSession,
        redis_client: redis.Redis,
    ) -> tuple[str, str]:
        """
        Accept WebSocket connection and set up conversation.

        Returns:
            tuple[connection_id, conversation_id]
        """
        await websocket.accept()

        # Generate unique connection ID
        connection_id = str(uuid.uuid4())

        # Get or create conversation using existing service
        conversation_service = ConversationService(db, redis_client)
        conversation = await conversation_service.get_or_create_conversation(
            visitor_id=visitor_id,
            conversation_id=conversation_id,
            connection_id=connection_id,
            ai_model_used="gpt-4",
        )

        conversation_id = str(conversation.id)

        # Store connection mappings
        self.active_connections[connection_id] = websocket
        self.connection_conversations[connection_id] = conversation_id

        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(connection_id)

        logger.info(
            f"WebSocket connected: connection_id={connection_id}, "
            f"conversation_id={conversation_id}, visitor_id={visitor_id}"
        )

        return connection_id, conversation_id

    async def disconnect(
        self,
        connection_id: str,
        db: AsyncSession,
    ) -> None:
        """Handle WebSocket disconnection."""

        # Update conversation status in database
        conversation_service = ConversationService(db, redis.Redis())
        await conversation_service.update_connection_on_disconnect(
            connection_id
        )

        # Clean up connection mappings
        conversation_id = self.connection_conversations.pop(
            connection_id, None
        )
        if (
            conversation_id
            and conversation_id in self.conversation_connections
        ):
            self.conversation_connections[conversation_id].discard(
                connection_id
            )
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]

        self.active_connections.pop(connection_id, None)

        logger.info(f"WebSocket disconnected: connection_id={connection_id}")

    async def send_personal_message(
        self,
        message: str,
        connection_id: str,
    ) -> None:
        """Send message to specific connection."""
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Connection might be dead, clean up
                await self._cleanup_dead_connection(connection_id)

    async def send_to_conversation(
        self,
        message: str,
        conversation_id: str,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """Send message to all connections in a conversation."""
        connection_ids = self.conversation_connections.get(
            conversation_id, set()
        )

        for (
            connection_id
        ) in (
            connection_ids.copy()
        ):  # Copy to avoid modification during iteration
            if exclude_connection and connection_id == exclude_connection:
                continue

            await self.send_personal_message(message, connection_id)

    async def broadcast_to_all(self, message: str) -> None:
        """Broadcast message to all active connections."""
        for connection_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, connection_id)

    async def handle_message(
        self,
        websocket: WebSocket,
        connection_id: str,
        db: AsyncSession,
        redis_client: redis.Redis,
    ) -> None:
        """Handle incoming WebSocket messages."""
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Validate message structure
                if "type" not in message_data:
                    await self.send_personal_message(
                        json.dumps({"error": "Message type required"}),
                        connection_id,
                    )
                    continue

                # Handle different message types
                if message_data["type"] == "user_message":
                    await self._handle_user_message(
                        message_data, connection_id, db, redis_client
                    )
                elif message_data["type"] == "heartbeat":
                    await self._handle_heartbeat(connection_id)
                else:
                    await self.send_personal_message(
                        json.dumps(
                            {
                                "error": f"Unknown message type: {message_data['type']}"
                            }
                        ),
                        connection_id,
                    )

        except WebSocketDisconnect:
            await self.disconnect(connection_id, db)
        except json.JSONDecodeError:
            await self.send_personal_message(
                json.dumps({"error": "Invalid JSON format"}), connection_id
            )
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_personal_message(
                json.dumps({"error": "Server error"}), connection_id
            )

    async def _handle_user_message(
        self,
        message_data: dict,
        connection_id: str,
        db: AsyncSession,
        redis_client: redis.Redis,
    ) -> None:
        """Handle user message and generate AI response."""
        conversation_id = self.connection_conversations.get(connection_id)
        if not conversation_id:
            await self.send_personal_message(
                json.dumps({"error": "No active conversation"}), connection_id
            )
            return

        content = message_data.get("content", "").strip()
        if not content:
            await self.send_personal_message(
                json.dumps({"error": "Message content required"}),
                connection_id,
            )
            return

        # Save user message
        message_service = MessageService(db, redis_client)
        user_message = await message_service.save_message(
            conversation_id=conversation_id,
            content=content,
            sender_type="user",
        )

        # Send confirmation to user
        await self.send_personal_message(
            json.dumps(
                {
                    "type": "message_received",
                    "message": {
                        "id": str(user_message.id),
                        "content": content,
                        "sender_type": "user",
                        "timestamp": user_message.timestamp.isoformat(),
                    },
                }
            ),
            connection_id,
        )

        # TODO: Generate AI response (placeholder for now)
        ai_response = f"AI response to: {content}"

        # Save AI message
        ai_message = await message_service.save_message(
            conversation_id=conversation_id,
            content=ai_response,
            sender_type="ai",
        )

        # Send AI response
        await self.send_personal_message(
            json.dumps(
                {
                    "type": "ai_response",
                    "message": {
                        "id": str(ai_message.id),
                        "content": ai_response,
                        "sender_type": "ai",
                        "timestamp": ai_message.timestamp.isoformat(),
                    },
                }
            ),
            connection_id,
        )

    async def _handle_heartbeat(self, connection_id: str) -> None:
        """Handle heartbeat message."""
        await self.send_personal_message(
            json.dumps(
                {
                    "type": "heartbeat_ack",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            connection_id,
        )

    async def _cleanup_dead_connection(self, connection_id: str) -> None:
        """Clean up a dead connection."""
        conversation_id = self.connection_conversations.pop(
            connection_id, None
        )
        if (
            conversation_id
            and conversation_id in self.conversation_connections
        ):
            self.conversation_connections[conversation_id].discard(
                connection_id
            )
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]

        self.active_connections.pop(connection_id, None)
        logger.info(f"Cleaned up dead connection: {connection_id}")

    def get_active_connections_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_conversation_connections_count(self, conversation_id: str) -> int:
        """Get number of connections for a specific conversation."""
        return len(self.conversation_connections.get(conversation_id, set()))


# Global connection manager instance
manager = ConnectionManager()
