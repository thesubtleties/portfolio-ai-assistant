from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.database import Conversation, Visitor


class ConversationService:
    @staticmethod
    def get_or_create_current_conversation(
        db: Session,
        visitor_id: str,
        connection_id: str,
        session_id: str,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Get active conversation for this browser session only, or create a new one if none exists.
        Args:
            db (Session): Database session for executing queries
            visitor_id (str): Unique visitor ID
            connection_id (str): Unique connection ID for the current session
            session_id (str): Unique session ID for the current session
            ai_model_used (Optional[str], optional): AI model used in the conversation. Defaults to None.
        """

        active_conversation = (
            db.query(Conversation)
            .filter(
                Conversation.visitor_id == visitor_id,
                Conversation.status.in_(
                    ["active_ai", "active_human", "escalation_pending"]
                ),
                Conversation.conversation_metadata.op("->>")("session_id")
                == session_id,
            )
            .order_by(Conversation.last_message_at.desc())
            .first()
        )

        if active_conversation:
            # Update connection_id for this Websocket connection
            active_conversation.conversation_metadata[
                "current_connection_id"
            ] = connection_id
            active_conversation.last_message_at = datetime.now(timezone.utc)
            db.commit()
            return active_conversation

        return ConversationService.create_conversation(
            db=db,
            visitor_id=visitor_id,
            connection_id=connection_id,
            session_id=session_id,
            ai_model_used=ai_model_used,
        )

    @staticmethod
    def create_conversation(
        db: Session,
        visitor_id: str,
        connection_id: str,
        session_id: str,
        ai_model_used: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        now = datetime.now(timezone.utc)

        conversation = Conversation(
            visitor_id=visitor_id,
            started_at=now,
            last_message_at=now,
            status="active_ai",
            ai_model_used=ai_model_used,
            conversation_metadata={
                "current_connection_id": connection_id,
                "session_id": session_id,
            },
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
