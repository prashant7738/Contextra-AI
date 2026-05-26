"""Add chats table and chat_id to documents

Revision ID: d2b5c3a1e9f2
Revises: ce1e8122e91a
Create Date: 2026-05-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2b5c3a1e9f2'
down_revision: Union[str, Sequence[str], None] = 'ce1e8122e91a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add timestamps to documents
    op.add_column('documents', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    
    # Add chat_id column (nullable first for existing data)
    op.add_column('documents', sa.Column('chat_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_documents_chat_id', 'documents', 'chats', ['chat_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_documents_chat_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'chat_id')
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'created_at')
    op.drop_table('chats')
