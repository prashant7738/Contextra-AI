"""Fix User model to have name and email

Revision ID: ce1e8122e91a
Revises: 
Create Date: 2026-05-25 07:08:52.440606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce1e8122e91a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "email" not in user_columns:
        op.add_column("users", sa.Column("email", sa.String(), nullable=True))
        op.create_unique_constraint("users_email_key", "users", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "email" in user_columns:
        op.drop_constraint("users_email_key", "users", type_="unique")
        op.drop_column("users", "email")
