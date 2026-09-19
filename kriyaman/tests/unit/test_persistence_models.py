import ast
from pathlib import Path
from persistence.db import Base
import persistence.models  # Register all models


def test_persistence_table_registration():
    """Verify that all 15 tables (core domain + evaluation + checkpoints) are registered in metadata."""
    expected_tables = {
        "memory_principals",
        "sessions",
        "conversation_turns",
        "documents",
        "document_chunks",
        "memories",
        "retrieval_records",
        "tool_calls",
        "runs",
        "run_events",
        "evaluation_runs",
        "evaluation_cases",
        "langgraph_checkpoints",
        "langgraph_checkpoint_blobs",
        "langgraph_checkpoint_writes",
    }

    registered_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - registered_tables
    assert not missing, f"Missing required persistence tables in metadata: {missing}"
    assert registered_tables == expected_tables


def test_migration_schema_covers_all_registered_models():
    """Verify that the Alembic migration script defines every table registered in Base.metadata."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    migration_file = root_dir / "persistence" / "migrations" / "versions" / "001_initial_schema.py"
    assert migration_file.exists(), f"Migration file not found at {migration_file}"

    with open(migration_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(migration_file))

    migrated_created_tables = set()
    migrated_dropped_tables = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "create_table" and node.args:
                if isinstance(node.args[0], ast.Constant):
                    migrated_created_tables.add(node.args[0].value)
            elif node.func.attr == "drop_table" and node.args:
                if isinstance(node.args[0], ast.Constant):
                    migrated_dropped_tables.add(node.args[0].value)

    registered_tables = set(Base.metadata.tables.keys())

    missing_in_upgrade = registered_tables - migrated_created_tables
    assert not missing_in_upgrade, f"Migration upgrade() is missing tables: {missing_in_upgrade}"

    missing_in_downgrade = registered_tables - migrated_dropped_tables
    assert not missing_in_downgrade, f"Migration downgrade() is missing drop_table for: {missing_in_downgrade}"


def test_vector_columns_present():
    """Verify that document_chunks and memories have embedding vector columns."""
    chunks_table = Base.metadata.tables["document_chunks"]
    assert "embedding" in chunks_table.columns

    memories_table = Base.metadata.tables["memories"]
    assert "embedding" in memories_table.columns


def test_table_foreign_keys():
    """Verify relationships and foreign key definitions."""
    sessions = Base.metadata.tables["sessions"]
    fk_targets = [fk.target_fullname for fk in sessions.foreign_keys]
    assert "memory_principals.id" in fk_targets

    chunks = Base.metadata.tables["document_chunks"]
    fk_targets = [fk.target_fullname for fk in chunks.foreign_keys]
    assert "documents.id" in fk_targets

    runs = Base.metadata.tables["runs"]
    fk_targets = [fk.target_fullname for fk in runs.foreign_keys]
    assert "sessions.id" in fk_targets
