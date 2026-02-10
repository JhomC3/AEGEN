# tests/unit/memory/test_sqlite_store.py
import os
from pathlib import Path

import pytest

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def temp_db():
    """Fixture para crear una DB temporal y limpiarla después."""
    db_path = "storage/test_memory.db"
    # Asegurar que el directorio storage existe
    Path("storage").mkdir(exist_ok=True)

    if os.path.exists(db_path):
        os.remove(db_path)

    store = SQLiteStore(db_path)
    await store.init_db(settings.SQLITE_SCHEMA_PATH)

    yield store

    await store.disconnect()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_init_db(temp_db):
    """Verifica que la DB se inicializa con las tablas correctas."""
    db = await temp_db.get_db()
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cursor:
        tables = [row[0] for row in await cursor.fetchall()]
        assert "memories" in tables
        assert "vector_memory_map" in tables
        assert "embedding_cache" in tables
        assert "profiles" in tables
        # memories_fts es una tabla virtual, puede no aparecer en sqlite_master normal o si

    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_fts'"
    ) as cursor:
        assert await cursor.fetchone() is not None


@pytest.mark.asyncio
async def test_insert_and_load_memory(temp_db):
    """Prueba la inserción y recuperación de una memoria."""
    memory_id = await temp_db.insert_memory(
        chat_id="test_chat",
        content="Contenido de prueba",
        content_hash="hash_1",
        memory_type="fact",
        metadata={"key": "value"},
    )
    assert memory_id > 0

    db = await temp_db.get_db()
    async with db.execute(
        "SELECT content FROM memories WHERE id = ?", (memory_id,)
    ) as cursor:
        row = await cursor.fetchone()
        assert row["content"] == "Contenido de prueba"


@pytest.mark.asyncio
async def test_hash_exists(temp_db):
    """Verifica la detección de duplicados por hash."""
    await temp_db.insert_memory("chat1", "content1", "hash_abc", "fact")
    assert await temp_db.hash_exists("hash_abc") is True
    assert await temp_db.hash_exists("non_existent") is False


@pytest.mark.asyncio
async def test_profile_operations(temp_db):
    """Prueba guardar y cargar perfiles."""
    profile_data = {"name": "Test User", "preferences": {"theme": "dark"}}
    await temp_db.save_profile("chat_123", profile_data)

    loaded = await temp_db.load_profile("chat_123")
    assert loaded == profile_data

    # Update
    profile_data["name"] = "Updated Name"
    await temp_db.save_profile("chat_123", profile_data)
    assert (await temp_db.load_profile("chat_123"))["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_vector_cleanup_trigger(temp_db):
    """
    PRUEBA CRÍTICA: Verifica que al borrar una memoria,
    se limpie el vector físico automáticamente.
    """
    # 1. Insertar memoria
    memory_id = await temp_db.insert_memory("chat1", "text", "hash1", "fact")

    # 2. Insertar vector
    fake_embedding = [0.1] * 768
    await temp_db.insert_vector(memory_id, fake_embedding)

    db = await temp_db.get_db()

    # Verificar que existen
    async with db.execute("SELECT COUNT(*) FROM memory_vectors") as c:
        assert (await c.fetchone())[0] == 1
    async with db.execute("SELECT COUNT(*) FROM vector_memory_map") as c:
        assert (await c.fetchone())[0] == 1

    # 3. Borrar memoria
    await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    await db.commit()

    # 4. Verificar limpieza en cascada
    # Trigger 1: memories -> memories_fts (implícito en sqlite)
    # Trigger 2: memories -> vector_memory_map (ON DELETE CASCADE)
    async with db.execute("SELECT COUNT(*) FROM vector_memory_map") as c:
        assert (await c.fetchone())[0] == 0

    # Trigger 3 (NUESTRO): vector_memory_map -> memory_vectors
    async with db.execute("SELECT COUNT(*) FROM memory_vectors") as c:
        assert (await c.fetchone())[
            0
        ] == 0, "El vector físico no se borró automáticamente"
