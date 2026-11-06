"""create embeddings table (previously only created by create_all at startup)

Revision ID: c8f1e5a3d2b7
Revises: a9d4e2c7b1f3
Create Date: 2026-11-06 12:30:00.000000

Idempotent: existing databases already have this table and its indexes (made
by Base.metadata.create_all), so every statement is IF NOT EXISTS and
upgrading them is a no-op.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c8f1e5a3d2b7'
down_revision: Union[str, Sequence[str], None] = 'a9d4e2c7b1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id UUID PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users (id),
            document_id INTEGER REFERENCES documents (id),
            chat_id INTEGER REFERENCES chats (id),
            content TEXT NOT NULL,
            embedding vector(384) NOT NULL,
            chunk_metadata JSONB,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_user_id ON embeddings (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_document_id ON embeddings (document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_chat_id ON embeddings (chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_user_chat ON embeddings (user_id, chat_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_embedding_cosine ON embeddings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    # Not dropped: on databases that predate this migration the table holds
    # every document's vectors, and downgrading must never destroy them.
    pass
