import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Text,
    JSON,
    TIMESTAMP,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class HumanAgent(Base):
    __tablename__ = "human_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    assigned_conversations = relationship(
        "Conversation",
        back_populates="assigned_human_agent",
        foreign_keys="Conversation.assigned_human_agent_id",
    )
    sent_messages = relationship(
        "Message",
        back_populates="sender_human_agent",
        foreign_keys="Message.human_agent_id",
    )

    def __repr__(self):
        return f"<HumanAgent(id={self.id}, username={self.username}, display_name={self.display_name}, email={self.email})>"


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint_id = Column(Text, unique=True, nullable=False, index=True)
    first_seen_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent_raw = Column(Text, nullable=True)
    ip_address_hash = Column(String(128), nullable=True)
    profile_data = Column(JSONB, nullable=True)
    notes_by_agent = Column(Text, nullable=True)

    conversations = relationship(
        "Conversation", back_populates="visitor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Visitor(id={self.id}, fingerprint_id={self.fingerprint_id}, first_seen_at={self.first_seen_at})>"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id"),
        nullable=False,
        index=True,
    )
    started_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    last_message_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(
        String(50), nullable=False, default="active_ai", index=True
    )
    assigned_human_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("human_agents.id"),
        nullable=True,
        index=True,
    )
    ai_model_used = Column(String(100), nullable=True)
    conversation_metadata = Column(JSONB, nullable=True)

    visitor = relationship("Visitor", back_populates="conversations")
    assigned_human_agent = relationship(
        "HumanAgent",
        back_populates="assigned_conversations",
        foreign_keys=[assigned_human_agent_id],
    )
    messages = relationship(
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
        return f"<Conversation(id={self.id}, visitor_id={self.visitor_id}, started_at={self.started_at}, status={self.status})>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    sender_type = Column(String(50), nullable=False, index=True)
    human_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("human_agents.id"),
        nullable=True,
        index=True,
    )
    content = Column(Text, nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    message_metadata = Column(JSONB, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    sender_human_agent = relationship(
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
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type={self.sender_type}, timestamp={self.timestamp})>"


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    last_indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    checksum = Column(String(128), nullable=True)

    def __repr__(self):
        return f"<KnowledgeSource(id={self.id}, source_name={self.source_name}, last_indexed_at={self.last_indexed_at})>"
