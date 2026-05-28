# tests/unit/memory/test_worker_edges.py
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.memory.consolidation_worker import ConsolidationManager
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def worker_db():
    db_path = Path("storage/test_worker_edges.db")
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
async def test_transversal_edges_generation(worker_db):
    db = await worker_db.get_db()
    manager = ConsolidationManager()

    # 1. Insertar hechos atómicos candidatos
    await db.execute(
        "INSERT INTO memories (id, chat_id, namespace, content, content_hash, memory_type, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            10,
            "chat_t1",
            "user",
            "Déficit calórico",
            "hash_t1",
            "fact",
            '{"fact_key": "calorias"}',
        ),
    )
    await db.execute(
        "INSERT INTO memories (id, chat_id, namespace, content, content_hash, memory_type, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            20,
            "chat_t1",
            "user",
            "Irritabilidad",
            "hash_t2",
            "fact",
            '{"fact_key": "irritabilidad"}',
        ),
    )
    await db.commit()

    # 2. Mock de la llamada LLM a Gemini
    mock_chain = AsyncMock()
    # Retorna JSON con la arista identificada
    mock_json_response = '[{"origen": "calorias", "destino": "irritabilidad", "tipo": "causa", "peso": 0.85, "evidencia": "Déficit calórico causa irritabilidad"}]'
    mock_response = MagicMock()
    mock_response.content = mock_json_response
    mock_chain.ainvoke.return_value = mock_response

    raw_buffer = [
        {"role": "user", "content": "Me siento muy irritable hoy"},
        {
            "role": "assistant",
            "content": "Tal vez sea porque estás en un déficit calórico.",
        },
    ]

    with (
        patch("src.core.dependencies.get_sqlite_store", return_value=worker_db),
        patch(
            "langchain_core.prompts.ChatPromptTemplate.__or__", return_value=mock_chain
        ),
    ):
        await manager._generate_transversal_edges("chat_t1", raw_buffer)

        # 3. Comprobar que la arista fue insertada en la DB
        async with db.execute(
            "SELECT origen_id, destino_id, tipo_relacion, peso, evidencia FROM memory_edges"
        ) as cursor:
            rows = await cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 10  # origen_id (calorias)
            assert rows[0][1] == 20  # destino_id (irritabilidad)
            assert rows[0][2] == "causa"
            assert rows[0][3] == 0.85
            assert rows[0][4] == "Déficit calórico causa irritabilidad"
