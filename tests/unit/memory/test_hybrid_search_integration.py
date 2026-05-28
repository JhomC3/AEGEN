# tests/unit/memory/test_hybrid_search_integration.py
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.memory.hybrid_search import HybridSearch
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def store():
    db_path = Path("storage/test_search_filter.db")
    if db_path.exists():
        db_path.unlink()
    store = SQLiteStore(str(db_path))
    await store.connect()
    await store.init_db(settings.SQLITE_SCHEMA_PATH)
    from src.memory.migration import apply_migrations

    await apply_migrations(store)

    yield store

    await store.disconnect()
    if db_path.exists():
        db_path.unlink()


@pytest.mark.asyncio
async def test_search_excludes_inactive_memories(store):
    """Soft-deleted memories must not appear in search results."""
    hybrid = HybridSearch(store)

    # Insert an active and an inactive memory
    mid1 = await store.insert_memory(
        "chat1", "active memory about dogs", "hash_active_1", "fact"
    )
    mid2 = await store.insert_memory(
        "chat1", "inactive memory about dogs", "hash_inactive_1", "fact"
    )

    # Soft-delete mid2
    await store.soft_delete_memories([mid2])

    # search_by_type should only return active
    results = await hybrid.search_by_type("fact", chat_id="chat1")
    result_ids = {r["id"] for r in results}
    assert mid1 in result_ids
    assert mid2 not in result_ids


@pytest.mark.asyncio
async def test_hybrid_search_excludes_inactive_memories(store):
    """Hybrid search must exclude soft-deleted memories during hydration."""
    hybrid = HybridSearch(store)

    # Insert memories
    mid1 = await store.insert_memory("chat1", "active content", "hash_h1", "fact")
    mid2 = await store.insert_memory("chat1", "deleted content", "hash_h2", "fact")

    # Soft-delete mid2
    await store.soft_delete_memories([mid2])

    # Mock search components to return both IDs
    with (
        patch.object(
            hybrid.vector_search,
            "search",
            AsyncMock(return_value=[(mid1, 0.1), (mid2, 0.2)]),
        ),
        patch.object(
            hybrid.keyword_search,
            "search",
            AsyncMock(return_value=[(mid1, 1.0), (mid2, 0.5)]),
        ),
        patch.object(
            hybrid.embedding_service,
            "embed_query",
            AsyncMock(return_value=[0.1] * 768),
        ),
    ):
        results = await hybrid.search("test", chat_id="chat1")

        result_ids = {r["id"] for r in results}
        assert mid1 in result_ids
        assert mid2 not in result_ids
