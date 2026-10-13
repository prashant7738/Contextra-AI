"""replace user token limits with a monthly USD budget

Revision ID: e7a3c9b5d1f4
Revises: c4e8a2f1d6b7
Create Date: 2026-10-13 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a3c9b5d1f4'
down_revision: Union[str, Sequence[str], None] = 'c4e8a2f1d6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every existing user starts on the default $1.00 / month budget.
    op.add_column('users', sa.Column('monthly_budget_micro_usd', sa.BigInteger(), server_default=sa.text('1000000'), nullable=False))
    op.add_column('users', sa.Column('spent_micro_usd', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('spend_month', sa.String(length=7), nullable=True))
    op.drop_column('users', 'tokens_used')
    op.drop_column('users', 'token_limit')


def downgrade() -> None:
    op.add_column('users', sa.Column('token_limit', sa.Integer(), server_default=sa.text('25000'), nullable=False))
    op.add_column('users', sa.Column('tokens_used', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.drop_column('users', 'spend_month')
    op.drop_column('users', 'spent_micro_usd')
    op.drop_column('users', 'monthly_budget_micro_usd')
