"""add_user_token_limits

Revision ID: f2d9a1b7c8e4
Revises: a1bef0049494
Create Date: 2026-07-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2d9a1b7c8e4'
down_revision: Union[str, Sequence[str], None] = 'a1bef0049494'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('token_limit', sa.Integer(), server_default=sa.text('25000'), nullable=False))
    op.add_column('users', sa.Column('tokens_used', sa.Integer(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'tokens_used')
    op.drop_column('users', 'token_limit')