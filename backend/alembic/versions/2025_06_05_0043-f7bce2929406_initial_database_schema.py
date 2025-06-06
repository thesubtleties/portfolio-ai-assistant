"""Initial database schema

Revision ID: f7bce2929406
Revises: 
Create Date: 2025-06-05 00:43:28.049962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7bce2929406'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('human_agents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_human_agents_email'), 'human_agents', ['email'], unique=True)
    op.create_index(op.f('ix_human_agents_username'), 'human_agents', ['username'], unique=True)
    op.create_table('knowledge_sources',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('last_indexed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('checksum', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_sources_source_name'), 'knowledge_sources', ['source_name'], unique=True)
    op.create_table('visitors',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('fingerprint_id', sa.Text(), nullable=False),
    sa.Column('first_seen_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_agent_raw', sa.Text(), nullable=True),
    sa.Column('ip_address_hash', sa.String(length=128), nullable=True),
    sa.Column('profile_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('notes_by_agent', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_visitors_fingerprint_id'), 'visitors', ['fingerprint_id'], unique=True)
    op.create_table('conversations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('visitor_id', sa.UUID(), nullable=False),
    sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_message_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('assigned_human_agent_id', sa.UUID(), nullable=True),
    sa.Column('ai_model_used', sa.String(length=100), nullable=True),
    sa.Column('conversation_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("status IN ('active_ai', 'escalated', 'active_human', 'ended')", name='valid_conversation_status'),
    sa.ForeignKeyConstraint(['assigned_human_agent_id'], ['human_agents.id'], ),
    sa.ForeignKeyConstraint(['visitor_id'], ['visitors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_assigned_human_agent_id'), 'conversations', ['assigned_human_agent_id'], unique=False)
    op.create_index(op.f('ix_conversations_started_at'), 'conversations', ['started_at'], unique=False)
    op.create_index(op.f('ix_conversations_status'), 'conversations', ['status'], unique=False)
    op.create_index(op.f('ix_conversations_visitor_id'), 'conversations', ['visitor_id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('sender_type', sa.String(length=50), nullable=False),
    sa.Column('human_agent_id', sa.UUID(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('message_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("sender_type IN ('visitor', 'ai', 'human_agent')", name='valid_sender_type'),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.ForeignKeyConstraint(['human_agent_id'], ['human_agents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_human_agent_id'), 'messages', ['human_agent_id'], unique=False)
    op.create_index(op.f('ix_messages_sender_type'), 'messages', ['sender_type'], unique=False)
    op.create_index(op.f('ix_messages_timestamp'), 'messages', ['timestamp'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_messages_timestamp'), table_name='messages')
    op.drop_index(op.f('ix_messages_sender_type'), table_name='messages')
    op.drop_index(op.f('ix_messages_human_agent_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_conversations_visitor_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_status'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_started_at'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_assigned_human_agent_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_visitors_fingerprint_id'), table_name='visitors')
    op.drop_table('visitors')
    op.drop_index(op.f('ix_knowledge_sources_source_name'), table_name='knowledge_sources')
    op.drop_table('knowledge_sources')
    op.drop_index(op.f('ix_human_agents_username'), table_name='human_agents')
    op.drop_index(op.f('ix_human_agents_email'), table_name='human_agents')
    op.drop_table('human_agents')
    # ### end Alembic commands ###
