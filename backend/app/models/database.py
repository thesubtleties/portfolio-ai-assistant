from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    ForeignKey,
    Text,
    TIMESTAMP,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class HumanAgent(Base):
    __tablename__ = "human_agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    assigned_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="assigned_human_agent",
        foreign_keys="Conversation.assigned_human_agent_id",
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="sender_human_agent",
        foreign_keys="Message.human_agent_id",
    )

    def __repr__(self):
        return f"<HumanAgent(id={self.id}, username={self.username}, display_name={self.display_name}, email={self.email})>"


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fingerprint_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    user_agent_raw: Mapped[str | None] = mapped_column(Text)
    ip_address_hash: Mapped[str | None] = mapped_column(String(128))
    profile_data: Mapped[dict | None] = mapped_column(JSONB)
    notes_by_agent: Mapped[str | None] = mapped_column(Text)

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="visitor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Visitor(id={self.id}, fingerprint_id={self.fingerprint_id}, first_seen_at={self.first_seen_at})>"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    visitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visitors.id"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), index=True
    )
    last_message_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(
        String(50), default="active_ai", index=True
    )
    assigned_human_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("human_agents.id"), index=True
    )
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    conversation_metadata: Mapped[dict | None] = mapped_column(JSONB)
    visitor: Mapped["Visitor"] = relationship(
        "Visitor", back_populates="conversations"
    )
    assigned_human_agent: Mapped[HumanAgent | None] = relationship(
        "HumanAgent",
        back_populates="assigned_conversations",
        foreign_keys="Conversation.assigned_human_agent_id",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.timestamp",
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('active_ai', 'escalated', 'active_human', 'ended')",
            name="valid_conversation_status",
        ),
    )

    def __repr__(self):
        return (
            f"<Conversation(id={self.id}, visitor_id={self.visitor_id}, "
            f"started_at={self.started_at}, status={self.status})>"
        )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    sender_type: Mapped[str] = mapped_column(String(50), index=True)
    human_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("human_agents.id"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), index=True
    )
    message_metadata: Mapped[dict | None] = mapped_column(JSONB)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    sender_human_agent: Mapped[HumanAgent | None] = relationship(
        "HumanAgent",
        back_populates="sent_messages",
        foreign_keys=[human_agent_id],
    )
    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('visitor', 'ai', 'human_agent')",
            name="valid_sender_type",
        ),
    )

    def __repr__(self):
        return (
            f"<Message(id={self.id}, conversation_id={self.conversation_id}, "
            f"sender_type={self.sender_type}, timestamp={self.timestamp})>"
        )


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    checksum: Mapped[str | None] = mapped_column(String(128))

    def __repr__(self):
        return (
            f"<KnowledgeSource(id={self.id}, source_name={self.source_name}, "
            f"last_indexed_at={self.last_indexed_at})>"
        )
