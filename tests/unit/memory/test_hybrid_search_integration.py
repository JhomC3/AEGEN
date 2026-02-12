# tests/unit/memory/test_hybrid_search_integration.py
import os
from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.memory.hybrid_search import HybridSearch
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def search_db():
    """Fixture para crear una DB temporal y limpiarla después."""
    db_path = "storage/test_search_filter.db"

    if os.path.exists(db_path):
        os.remove(db_path)

    store = SQLiteStore(db_path)
    await store.init_db(settings.SQLITE_SCHEMA_PATH)
    from src.memory.migration import apply_migrations

    await apply_migrations(store)

    yield store

    await store.disconnect()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_search_excludes_inactive_memories(search_db):
    """Soft-deleted memories must not appear in search results."""
    hybrid = HybridSearch(search_db)

    # Insert an active and an inactive memory
    mid1 = await search_db.insert_memory(
        "chat1", "active memory about dogs", "hash_active_1", "fact"
    )
    mid2 = await search_db.insert_memory(
        "chat1", "inactive memory about dogs", "hash_inactive_1", "fact"
    )

    # Soft-delete mid2
    await search_db.soft_delete_memories([mid2])

    # search_by_type should only return active
    results = await hybrid.search_by_type("fact", chat_id="chat1")
    result_ids = {r["id"] for r in results}
    assert mid1 in result_ids
    assert mid2 not in result_ids


@pytest.mark.asyncio
async def test_hybrid_search_excludes_inactive_memories(search_db):
    """Hybrid search must exclude soft-deleted memories during hydration."""
    hybrid = HybridSearch(search_db)

    # Insert memories
    mid1 = await search_db.insert_memory("chat1", "active content", "hash_h1", "fact")
    mid2 = await search_db.insert_memory("chat1", "deleted content", "hash_h2", "fact")

    # Soft-delete mid2
    await search_db.soft_delete_memories([mid2])

    # Mock search components to return both IDs
    with patch.object(
        hybrid.vector_search,
        "search",
        AsyncMock(return_value=[(mid1, 0.1), (mid2, 0.2)]),
    ):
        with patch.object(
            hybrid.keyword_search,
            "search",
            AsyncMock(return_value=[(mid1, 1.0), (mid2, 0.5)]),
        ):
            with patch.object(
                hybrid.embedding_service,
                "embed_query",
                AsyncMock(return_value=[0.1] * 768),
            ):
                results = await hybrid.search("test", chat_id="chat1")

                result_ids = {r["id"] for r in results}
                assert mid1 in result_ids
                assert mid2 not in result_ids
