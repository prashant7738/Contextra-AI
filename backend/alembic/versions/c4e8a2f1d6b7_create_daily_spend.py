"""create_daily_spend

Revision ID: c4e8a2f1d6b7
Revises: b3f7c9d1a2e5
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a2f1d6b7'
down_revision: Union[str, Sequence[str], None] = 'b3f7c9d1a2e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'daily_spend',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('spent_micro_usd', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('day'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('daily_spend')
