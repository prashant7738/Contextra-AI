"""job queue bookkeeping on ingestion_tasks and summary_tasks

Revision ID: e5b2c8d4f6a1
Revises: d3a7f9c2e8b4
Create Date: 2026-11-06 16:30:00.000000

Adds attempt counters, worker heartbeats and the inputs workers need, so jobs
are claimed from the database and survive process restarts. Additive only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b2c8d4f6a1'
down_revision: Union[str, Sequence[str], None] = 'd3a7f9c2e8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ingestion_tasks', sa.Column('use_ocr', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('ingestion_tasks', sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('ingestion_tasks', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ingestion_tasks', sa.Column('document_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_ingestion_tasks_document_id', 'ingestion_tasks', 'documents', ['document_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('ix_ingestion_tasks_status', 'ingestion_tasks', ['status'], unique=False)

    op.add_column('summary_tasks', sa.Column('params', sa.JSON(), nullable=True))
    op.add_column('summary_tasks', sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('summary_tasks', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_summary_tasks_status', 'summary_tasks', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_summary_tasks_status', table_name='summary_tasks')
    op.drop_column('summary_tasks', 'locked_at')
    op.drop_column('summary_tasks', 'attempts')
    op.drop_column('summary_tasks', 'params')
    op.drop_index('ix_ingestion_tasks_status', table_name='ingestion_tasks')
    op.drop_constraint('fk_ingestion_tasks_document_id', 'ingestion_tasks', type_='foreignkey')
    op.drop_column('ingestion_tasks', 'document_id')
    op.drop_column('ingestion_tasks', 'locked_at')
    op.drop_column('ingestion_tasks', 'attempts')
    op.drop_column('ingestion_tasks', 'use_ocr')
