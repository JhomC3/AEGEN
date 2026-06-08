# tests/integration/test_memory_e2e.py
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager


@pytest.fixture
async def memory_system():
    db_path = Path("storage/test_memory_e2e.db")
    Path("storage").mkdir(exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = SQLiteStore(str(db_path))
    await store.connect()
    await store.init_db(settings.SQLITE_SCHEMA_PATH)

    # Mock de Embeddings para evitar llamadas a API real
    with patch("src.memory.embeddings.EmbeddingService.embed_texts") as mock_embed:
        # Retornar vectores fijos de 768 dims
        def side_effect(texts, task_type="RETRIEVAL_DOCUMENT"):
            return [[0.1 * (i + 1)] * 768 for i in range(len(texts))]

        mock_embed.side_effect = side_effect

        with patch("src.memory.embeddings.EmbeddingService.embed_query") as mock_query:
            mock_query.return_value = [0.1] * 768

            manager = VectorMemoryManager(store)
            yield manager, store

    await store.disconnect()
    if db_path.exists():
        db_path.unlink()


@pytest.mark.asyncio
async def test_full_memory_cycle(memory_system):
    manager, store = memory_system
    chat_id = "integration_test_user"

    # 1. Ingestar contenido largo (debería generar múltiples chunks)
    long_text = (
        "El sistema AEGEN utiliza una arquitectura de agentes especialistas. "
        "La memoria local-first se basa en SQLite y sqlite-vec para eficiencia. "
        "Esto permite que los datos del usuario permanezcan privados y accesibles sin latencia de red. "  # noqa: E501
        "Los perfiles psicológicos evolucionan con cada interacción."
    )

    # Reducimos tamaño de chunk y overlap para forzar múltiples fragmentos en el test
    with (
        patch.object(manager.pipeline.chunker, "chunk_size", 20),
        patch.object(manager.pipeline.chunker, "chunk_overlap", 5),
    ):
        new_chunks = await manager.store_context(
            user_id=chat_id, content=long_text, context_type=MemoryType.DOCUMENT
        )

        assert new_chunks > 1
        print(f"✅ Ingeridos {new_chunks} fragmentos")

        # 2. Verificar que están en la DB (el documento padre + los chunks hijos)
        db = await store.get_db()
        async with db.execute(
            "SELECT COUNT(*) FROM memories WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            assert count >= new_chunks

        # 5. Deduplicación
        # Intentar ingerir exactamente lo mismo
        dup_chunks = await manager.store_context(
            user_id=chat_id, content=long_text, context_type=MemoryType.DOCUMENT
        )
        assert dup_chunks == 0
        print("✅ Deduplicación SHA-256 verificada")

    # 3. Búsqueda Híbrida
    # Probamos búsqueda semántica (que será mockeada pero fluye por el sistema)
    results = await manager.retrieve_context(
        user_id=chat_id,
        query="arquitectura de agentes",
        limit=2,
        namespace=f"user_{chat_id}",
    )

    assert len(results) > 0
    assert "content" in results[0]
    print(f"✅ Búsqueda retornó: {results[0]['content'][:50]}...")

    # 4. Operaciones de Perfil
    profile_data = {"identity": {"name": "Test Runner"}, "evolution": {"level": 5}}
    await store.save_profile(chat_id, profile_data)

    loaded_profile = await store.load_profile(chat_id)
    assert loaded_profile["identity"]["name"] == "Test Runner"
    assert loaded_profile["evolution"]["level"] == 5
    print("✅ Gestión de perfiles verificada")
