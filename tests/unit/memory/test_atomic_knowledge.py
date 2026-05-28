# tests/unit/memory/test_atomic_knowledge.py
from pathlib import Path

import pytest

from src.core.config import settings
from src.memory.knowledge_base import KnowledgeBaseManager
from src.memory.sqlite_store import SQLiteStore


@pytest.fixture
async def kb_store():
    db_path = Path("storage/test_kb_atomic.db")
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
async def test_save_knowledge_atomic(kb_store):
    from unittest.mock import patch

    kb_manager = KnowledgeBaseManager()

    test_kb = {
        "user_name": "Juan",
        "entities": [
            {
                "key": "profesion",
                "value": "ingeniero",
                "confidence": 0.9,
                "source_type": "explicit",
            }
        ],
        "preferences": [
            {
                "key": "calorias_meta",
                "value": "2000",
                "confidence": 0.8,
                "source_type": "explicit",
            }
        ],
        "medical": [],
        "relationships": [],
        "milestones": [],
    }

    # Usar mock temporal para get_sqlite_store para inyectar nuestra DB de test
    with patch("src.memory.knowledge_base.get_sqlite_store", return_value=kb_store):
        await kb_manager.save_knowledge("test_chat_kb", test_kb)

        # Verificar carga atómica desde SQLite
        loaded = await kb_manager.load_knowledge("test_chat_kb")

        print("LOADED KB =", loaded)

        assert loaded["user_name"] == "Juan"

        # Verificar profesión
        prof = next(item for item in loaded["entities"] if item["key"] == "profesion")
        assert prof["value"] == "ingeniero"

        # Verificar calorías meta
        cal = next(
            item for item in loaded["preferences"] if item["key"] == "calorias_meta"
        )
        assert cal["value"] == "2000"
