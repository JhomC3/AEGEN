# tests/unit/memory/test_source_skill.py
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def skill_db():
    db_path = Path("storage/test_source_skill.db")
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
async def test_pipeline_stores_source_skill(skill_db):
    # Mock embedding API
    with patch("src.memory.ingestion_pipeline.EmbeddingService") as mock_emb_class:
        mock_emb = mock_emb_class.return_value
        mock_emb.embed_texts = AsyncMock(return_value=[[0.1] * 768])

        pipeline = IngestionPipeline(skill_db)
        await pipeline.process_text(
            chat_id="test_chat_skill",
            text="This is a test summary for CBT.",
            memory_type="conversation",
            source_skill="cbt_therapeutic",
        )

    db = await skill_db.get_db()
    async with db.execute(
        "SELECT source_skill FROM memories WHERE chat_id = 'test_chat_skill'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row[0] == "cbt_therapeutic"
