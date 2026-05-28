# tests/unit/memory/test_hierarchical_ingestion.py
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def hier_db():
    db_path = Path("storage/test_hierarchical.db")
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
async def test_hierarchical_ingestion_flow(hier_db):
    pipeline = IngestionPipeline(hier_db)

    # 1. Simular segmentación semántica
    # Estructura Nivel 3 (Padre) y Hijos Nivel 4 vinculados
    mock_chunks = [
        {
            "content": "Marco Teórico de Distorsiones Cognitivas",
            "domain": "psychology",
            "children": [
                {
                    "content": "El catastrofismo magnifica el peor escenario.",
                    "domain": "psychology",
                },
                {
                    "content": "La polarización ve todo en extremos blanco o negro.",
                    "domain": "psychology",
                },
            ],
        }
    ]

    # Mock de SemanticChunker para retornar esta estructura
    with (
        patch(
            "src.memory.semantic_chunker.SemanticChunker.chunk_semantically",
            return_value=mock_chunks,
        ),
        patch("src.memory.ingestion_pipeline.EmbeddingService") as mock_emb_class,
    ):
        mock_emb = mock_emb_class.return_value
        mock_emb.embed_texts = AsyncMock(return_value=[[0.1] * 768, [0.1] * 768])

        # 2. Ejecutar ingesta con use_semantic_chunker=True
        count = await pipeline.process_text(
            chat_id="global_doc_1",
            text="Un texto largo de distorsiones...",
            use_semantic_chunker=True,
            namespace="global",
            source_skill="global_knowledge",
        )

        assert count == 3  # 1 Padre + 2 Hijos = 3 registros creados

    # 3. Comprobar que en SQLite se guardó el parent_id relacionando a los hijos
    db = await hier_db.get_db()
    async with db.execute(
        "SELECT id, parent_id, content, memory_type FROM memories WHERE chat_id = 'global_doc_1'"
    ) as cursor:
        rows = await cursor.fetchall()

        # Debemos encontrar el padre
        parent = next(r for r in rows if r[3] == "document_parent")
        parent_id = parent[0]
        assert parent[1] is None  # Padre no tiene parent_id

        # Los hijos deben tener parent_id == parent_id
        children = [r for r in rows if r[3] == "document"]
        assert len(children) == 2
        for child in children:
            assert child[1] == parent_id  # Link jerárquico
