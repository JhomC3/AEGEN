# tests/unit/memory/test_ingestion_provenance.py
import os
from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def pipeline_db():
    db_path = "storage/test_ingestion_prov.db"
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
async def test_pipeline_passes_provenance_to_store(pipeline_db):
    """Provenance fields in metadata must be stored as columns in memories."""
    # Mock EmbeddingService to avoid API calls and timeouts
    with patch("src.memory.ingestion_pipeline.EmbeddingService") as mock_emb_class:
        mock_emb = mock_emb_class.return_value
        mock_emb.embed_texts = AsyncMock(return_value=[[0.1] * 768])

        pipeline = IngestionPipeline(pipeline_db)
        count = await pipeline.process_text(
            chat_id="test_chat",
            text="The user mentioned feeling anxious about work.",
            memory_type="fact",
            metadata={
                "source_type": "inferred",
                "confidence": 0.7,
                "sensitivity": "high",
                "evidence": "me siento ansioso por el trabajo",
            },
        )
        assert count > 0

    db = await pipeline_db.get_db()
    async with db.execute(
        "SELECT source_type, confidence, sensitivity, evidence FROM memories WHERE chat_id = 'test_chat'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row[0] == "inferred"
        assert row[1] == 0.7
        assert row[2] == "high"
        assert row[3] == "me siento ansioso por el trabajo"
