"""Add LangGraph checkpoint persistence tables.

Revision ID: 002_langgraph_checkpoints
Revises: 001_initial_schema
Create Date: 2026-09-18 22:34:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_langgraph_checkpoints"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "langgraph_checkpoints",
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_ns", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("checkpoint_id", sa.String(length=128), nullable=False),
        sa.Column("parent_checkpoint_id", sa.String(length=128), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_data", sa.LargeBinary(), nullable=False),
        sa.Column("metadata_type", sa.String(length=64), nullable=False),
        sa.Column("metadata_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id"),
    )

    op.create_table(
        "langgraph_checkpoint_blobs",
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_ns", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("channel", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("blob_data", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "thread_id", "checkpoint_ns", "channel", "version"
        ),
    )

    op.create_table(
        "langgraph_checkpoint_writes",
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_ns", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("checkpoint_id", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.String(length=128), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("value_data", sa.LargeBinary(), nullable=False),
        sa.Column("task_path", sa.String(length=256), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint(
            "thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"
        ),
    )


def downgrade() -> None:
    op.drop_table("langgraph_checkpoint_writes")
    op.drop_table("langgraph_checkpoint_blobs")
    op.drop_table("langgraph_checkpoints")
