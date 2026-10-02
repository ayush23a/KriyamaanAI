"""Add users table and resource ownership foreign keys.

Revision ID: 005_users_and_ownership
Revises: 004_document_chunks_tsv_gin
Create Date: 2026-09-30 14:30:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "005_users_and_ownership"
down_revision: Union[str, None] = "004_document_chunks_tsv_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("auth_provider", sa.String(length=32), nullable=False, server_default="clerk"),
        sa.Column("auth_subject", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_auth_subject", "users", ["auth_subject"], unique=True)

    # 2. Add user_id column to user-owned resources
    tables_to_add_user_id = [
        "sessions",
        "documents",
        "memories",
        "conversation_turns",
        "runs",
        "tool_calls",
        "client_credits",
        "memory_principals",
    ]

    for table in tables_to_add_user_id:
        op.add_column(
            table,
            sa.Column("user_id", sa.String(length=36), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_user_id_users",
            table,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"], unique=False)


def downgrade() -> None:
    tables_to_remove_user_id = [
        "memory_principals",
        "client_credits",
        "tool_calls",
        "runs",
        "conversation_turns",
        "memories",
        "documents",
        "sessions",
    ]

    for table in tables_to_remove_user_id:
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user_id_users", table_name=table, type_="foreignkey")
        op.drop_column(table, "user_id")

    op.drop_index("ix_users_auth_subject", table_name="users")
    op.drop_table("users")
