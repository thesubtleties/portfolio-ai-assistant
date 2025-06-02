from sqlalchemy.orm import Session
from app.models.database import Message, Conversation
from datetime import datetime, timezone, timedelta
from typing import List, Optional


class MessageService:
    @staticmethod
    def save_message(
        db: Session,
        conversation_id: str,
        sender_type: str,
        content: str,
        human_agent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Save a message to the conversation.
        Args:
            db (Session): Database session for executing queries
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

        db.add(message)

        # Update conversation's last_message_at timestamp
        conversation = (
            db.query(Conversation).filter_by(id=conversation_id).first()
        )
        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Message]:
        """Get messages for a specific conversation.
        Args:
            db (Session): Database session for executing queries
            conversation_id (str): ID of the conversation to fetch messages for
            limit (int, optional): Maximum number of messages to return. Defaults to 50.
        """
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .all()
        )
