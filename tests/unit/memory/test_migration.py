# tests/unit/memory/test_migration.py
import os

import pytest

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def migration_db():
    db_path = "test_migration.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = SQLiteStore(db_path)
    # Note: init_db uses settings.SQLITE_SCHEMA_PATH which we will update in Step 3
    await store.init_db(settings.SQLITE_SCHEMA_PATH)
    yield store
    await store.disconnect()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_migration_ensures_provenance_columns(migration_db):
    """After migration, all provenance columns must exist in memories table."""
    from src.memory.migration import apply_migrations

    await apply_migrations(migration_db)

    db = await migration_db.get_db()
    cursor = await db.execute("PRAGMA table_info(memories)")
    columns = {row[1] for row in await cursor.fetchall()}

    for col in (
        "source_type",
        "confidence",
        "sensitivity",
        "evidence",
        "confirmed_at",
        "is_active",
    ):
        assert col in columns, f"Column '{col}' missing after migration"


@pytest.mark.asyncio
async def test_migration_adds_indexes(migration_db):
    """Migration must create performance indexes."""
    from src.memory.migration import apply_migrations

    await apply_migrations(migration_db)

    db = await migration_db.get_db()
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in await cursor.fetchall()}

    assert "idx_memories_chat_namespace" in indexes
    assert "idx_memories_active" in indexes


@pytest.mark.asyncio
async def test_migration_is_idempotent(migration_db):
    """Running migration twice must not raise errors."""
    from src.memory.migration import apply_migrations

    await apply_migrations(migration_db)
    await apply_migrations(migration_db)  # Must not crash


@pytest.mark.asyncio
async def test_migration_defaults_existing_rows(migration_db):
    """Existing memories must get source_type='explicit', is_active=1."""
    # Insert a row BEFORE migration (with old schema columns only)
    db = await migration_db.get_db()
    # Note: We use a raw execute here to simulate an old state
    await db.execute(
        "INSERT INTO memories (chat_id, namespace, content, content_hash, memory_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("test", "user", "test content", "hash_test_1", "fact"),
    )
    await db.commit()

    from src.memory.migration import apply_migrations

    await apply_migrations(migration_db)

    async with db.execute(
        "SELECT source_type, confidence, is_active FROM memories WHERE content_hash = 'hash_test_1'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row[0] == "explicit"  # source_type default
        assert row[1] == 1.0  # confidence default
        assert row[2] == 1  # is_active default
