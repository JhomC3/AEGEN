# tests/unit/memory/test_embedding_cache.py
from unittest.mock import patch

import pytest

from src.core.config import settings
from src.memory.embeddings import EmbeddingService
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def temp_store():
    import tempfile
    from pathlib import Path

    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_cache.db"

    store = SQLiteStore(str(db_path))
    await store.connect()
    await store.init_db(settings.SQLITE_SCHEMA_PATH)
    from src.memory.migration import apply_migrations

    await apply_migrations(store)

    yield store

    await store.disconnect()
    db_path.unlink()
    Path(temp_dir).rmdir()


@pytest.mark.asyncio
async def test_embedding_cache_hit_and_miss(temp_store):
    service = EmbeddingService(store=temp_store)

    # Mock google API so we can verify if it's called
    with patch("google.generativeai.embed_content") as mock_embed:
        mock_embed.return_value = {"embedding": [[0.5] * 768]}

        # First call: cache miss (should hit API)
        res1 = await service.embed_texts(["hello world"])
        assert len(res1) == 1
        assert res1[0] == [0.5] * 768
        assert mock_embed.call_count == 1

        # Second call: cache hit (should NOT hit API)
        mock_embed.reset_mock()
        res2 = await service.embed_texts(["hello world"])
        assert len(res2) == 1
        assert res2[0] == [0.5] * 768
        assert mock_embed.call_count == 0  # 0 calls means it came from cache!
