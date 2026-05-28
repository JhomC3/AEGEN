# tests/unit/memory/test_migration_script.py
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.migrate_facts_to_atomic import migrate_legacy_facts
from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def mig_db():
    db_path = Path("storage/test_script_mig.db")
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
async def test_migrate_facts_script_execution(mig_db):
    db = await mig_db.get_db()

    # 1. Insertar hechos legacy (como JSON blobs completos en 'content')
    legacy_json = json.dumps({
        "user_name": "Juan Carlos",
        "entities": [{"key": "edad", "value": "30", "confidence": 0.95}],
    })

    await db.execute(
        "INSERT INTO memories (chat_id, namespace, content, content_hash, memory_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("chat_legacy_1", "user", legacy_json, "legacy_hash_abc", "fact"),
    )
    await db.commit()

    # Mocks para settings de DB y get_sqlite_store
    with (
        patch(
            "scripts.migrate_facts_to_atomic.settings.SQLITE_DB_PATH",
            new=str(mig_db.db_path),
        ),
        patch("src.memory.knowledge_base.get_sqlite_store", return_value=mig_db),
        patch("scripts.migrate_facts_to_atomic.SQLiteStore", return_value=mig_db),
        patch("src.memory.ingestion_pipeline.EmbeddingService") as mock_emb_class,
    ):
        mock_emb = mock_emb_class.return_value
        mock_emb.embed_texts = AsyncMock(return_value=[[0.1] * 768, [0.1] * 768])

        # 2. Ejecutar la migración
        await migrate_legacy_facts(store=mig_db)

        # 3. Comprobar que el registro legacy se marcó inactivo
        async with db.execute(
            "SELECT is_active FROM memories WHERE content_hash = 'legacy_hash_abc'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0  # Inactivo!

        # 4. Comprobar que se crearon los dos registros atómicos (user_name y edad)
        # Nota: El pipeline escribe namespace="user_{chat_id}" ahora, o el default
        async with db.execute(
            "SELECT content, metadata FROM memories WHERE chat_id = 'chat_legacy_1' AND is_active = 1"
        ) as cursor:
            atoms = await cursor.fetchall()
            print("ATOMS RETURNED IN TEST =", [(a[0], a[1]) for a in atoms])
            assert len(atoms) == 2

            contents = {a[0] for a in atoms}
            assert "Juan Carlos" in contents
            assert "30" in contents
