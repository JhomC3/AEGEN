# tests/unit/memory/test_hybrid_search.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.hybrid_search import HybridSearch


@pytest.mark.asyncio
async def test_rrf_logic():
    # Mock de dependencias
    store = MagicMock()
    hybrid = HybridSearch(store)

    # Simular resultados de búsqueda
    # (memory_id, distance/rank)
    hybrid.vector_search.search = AsyncMock(return_value=[(1, 0.1), (2, 0.2)])
    hybrid.keyword_search.search = AsyncMock(return_value=[(2, -1.5), (3, -1.0)])

    # Mock embedding y hydration
    hybrid.embedding_service.embed_query = AsyncMock(return_value=[0.1] * 768)

    # Mock de la base de datos para hidratación
    db = MagicMock()  # Usamos MagicMock para poder configurar __aenter__
    store.get_db = AsyncMock(return_value=db)

    cursor = AsyncMock()
    # Simular el comportamiento de context manager asíncrono para db.execute
    execute_cm = MagicMock()
    execute_cm.__aenter__ = AsyncMock(return_value=cursor)
    execute_cm.__aexit__ = AsyncMock(return_value=None)
    db.execute.return_value = execute_cm

    # Datos simulados de la DB
    rows = [
        {
            "id": 1,
            "content": "c1",
            "memory_type": "fact",
            "metadata": "{}",
            "chat_id": "u1",
            "created_at": "now",
        },
        {
            "id": 2,
            "content": "c2",
            "memory_type": "fact",
            "metadata": "{}",
            "chat_id": "u1",
            "created_at": "now",
        },
        {
            "id": 3,
            "content": "c3",
            "memory_type": "fact",
            "metadata": "{}",
            "chat_id": "u1",
            "created_at": "now",
        },
    ]
    cursor.fetchall.return_value = rows

    results = await hybrid.search("test query", limit=5)

    assert len(results) == 3
    # ID 2 debería estar primero porque aparece en ambas búsquedas (mejor RRF score)
    assert results[0]["id"] == 2
    assert results[1]["id"] in [1, 3]
