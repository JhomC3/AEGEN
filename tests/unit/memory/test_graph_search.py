# tests/unit/memory/test_graph_search.py
from pathlib import Path

import pytest

from src.core.config import settings
from src.memory.graph_search import expand_with_edges
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def graph_db():
    db_path = Path("storage/test_graph_search.db")
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
async def test_expand_with_edges_2_hops(graph_db):
    db = await graph_db.get_db()

    # 1. Insertar 3 memorias activas
    # ID 1: meta déficit calórico
    await db.execute(
        "INSERT INTO memories (id, chat_id, namespace, content, content_hash, memory_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "chat_g1", "user", "Déficit calórico sostenido", "hash_g1", "fact"),
    )
    # ID 2: irritabilidad
    await db.execute(
        "INSERT INTO memories (id, chat_id, namespace, content, content_hash, memory_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (2, "chat_g1", "user", "Alta irritabilidad matutina", "hash_g2", "fact"),
    )
    # ID 3: gasto impulsivo en café
    await db.execute(
        "INSERT INTO memories (id, chat_id, namespace, content, content_hash, memory_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (3, "chat_g1", "user", "Gasto impulsivo en café", "hash_g3", "fact"),
    )
    await db.commit()

    # 2. Insertar relaciones transversales (aristas)
    # 1 (déficit) -> causa -> 2 (irritabilidad) con peso 0.8
    # 2 (irritabilidad) -> causa -> 3 (gasto) con peso 0.9
    await db.execute(
        "INSERT INTO memory_edges (origen_id, destino_id, tipo_relacion, peso, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, 2, "causa", 0.8, "test"),
    )
    await db.execute(
        "INSERT INTO memory_edges (origen_id, destino_id, tipo_relacion, peso, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (2, 3, "causa", 0.9, "test"),
    )
    await db.commit()

    # 3. Consultar expansión partiendo de ID 1 (semilla)
    # Debe alcanzar ID 2 (1 salto) e ID 3 (2 saltos)
    results = await expand_with_edges(store=graph_db, seed_memory_ids=[1], max_hops=2)

    assert len(results) == 2
    # ID 2 (irritabilidad) debe ser el primero por peso acumulado 0.8 (1 salto)
    assert results[0]["id"] == 2
    assert results[0]["score"] == 0.8
    assert results[0]["hop_distance"] is True

    # ID 3 (gasto) debe ser el segundo por peso acumulado 0.8 * 0.9 = 0.72 (2 saltos)
    assert results[1]["id"] == 3
    assert results[1]["score"] == 0.72
