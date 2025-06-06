"""Add pgvector extension and portfolio content table

Revision ID: fc884737859d
Revises: f7bce2929406
Create Date: 2025-06-05 19:57:45.330110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = 'fc884737859d'
down_revision: Union[str, None] = 'f7bce2929406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('portfolio_content',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('knowledge_source_id', sa.UUID(), nullable=False),
    sa.Column('content_type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('content_chunk', sa.Text(), nullable=True),
    sa.Column('chunk_index', sa.Integer(), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.Column('content_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("content_type IN ('project', 'skill', 'experience', 'about', 'resume', 'general')", name='valid_content_type'),
    sa.ForeignKeyConstraint(['knowledge_source_id'], ['knowledge_sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_content_content_type'), 'portfolio_content', ['content_type'], unique=False)
    op.create_index(op.f('ix_portfolio_content_knowledge_source_id'), 'portfolio_content', ['knowledge_source_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_portfolio_content_knowledge_source_id'), table_name='portfolio_content')
    op.drop_index(op.f('ix_portfolio_content_content_type'), table_name='portfolio_content')
    op.drop_table('portfolio_content')
    # ### end Alembic commands ###
    
    # Drop pgvector extension (optional - might be used by other apps)
    # op.execute('DROP EXTENSION IF EXISTS vector')
