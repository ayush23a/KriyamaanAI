"""Add GIN functional index on document_chunks to_tsvector(content).

Revision ID: 004_document_chunks_tsv_gin
Revises: 003_client_credits
Create Date: 2026-09-26 12:55:00.000000
"""

from typing import Sequence, Union
from alembic import op


revision: str = "004_document_chunks_tsv_gin"
down_revision: Union[str, None] = "003_client_credits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsv "
        "ON document_chunks USING gin (to_tsvector('english', content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_content_tsv;")
