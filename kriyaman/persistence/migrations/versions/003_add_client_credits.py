"""Add client_credits table for BYOK and usage capping.

Revision ID: 003_client_credits
Revises: 002_langgraph_checkpoints
Create Date: 2026-09-23 11:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_client_credits"
down_revision: Union[str, None] = "002_langgraph_checkpoints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_credits",
        sa.Column("client_id", sa.String(length=128), primary_key=True),
        sa.Column("key_mode", sa.String(length=32), nullable=False, server_default="default"),
        sa.Column("default_spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("byok_spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("credit_limit_usd", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("client_credits")

