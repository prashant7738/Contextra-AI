"""add chat.local_id and unique constraint

Revision ID: a67dd3831c51
Revises: 00ea8f6ba1d3
Create Date: 2026-06-08 14:48:25.056124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a67dd3831c51'
down_revision: Union[str, Sequence[str], None] = '00ea8f6ba1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add column as nullable, populate values, then make it NOT NULL and add constraint
    op.add_column('chats', sa.Column('local_id', sa.Integer(), nullable=True))

    # Populate local_id per user using a row_number partitioned by user_id
    op.execute("""
    WITH numbered AS (
        SELECT id, row_number() OVER (PARTITION BY user_id ORDER BY id) AS rn
        FROM chats
    )
    UPDATE chats
    SET local_id = numbered.rn
    FROM numbered
    WHERE chats.id = numbered.id;
    """)

    # Set column to NOT NULL now that values are populated
    op.alter_column('chats', 'local_id', existing_type=sa.Integer(), nullable=False)

    # Create unique constraint on (user_id, local_id)
    op.create_unique_constraint('uq_chat_user_local_id', 'chats', ['user_id', 'local_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint and column
    op.drop_constraint('uq_chat_user_local_id', 'chats', type_='unique')
    op.drop_column('chats', 'local_id')
