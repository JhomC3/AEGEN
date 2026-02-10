# scripts/verify_phase2.py
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ingestion():
    print(f"\nTesting ingestion at: {settings.SQLITE_DB_PATH}")
    store = SQLiteStore(settings.SQLITE_DB_PATH)

    try:
        # 1. Init DB
        await store.init_db(settings.SQLITE_SCHEMA_PATH)
        print("✅ Schema initialized")

        pipeline = IngestionPipeline(store)
        chat_id = "test_verify_phase2"

        # 2. Test text (long enough for multiple chunks)
        text = """
        AEGEN es una plataforma de orquestación de agentes multi-especialista.
        Utiliza una arquitectura local-first para la memoria.
        MAGI es el asistente conversacional principal.

        El sistema de memoria utiliza SQLite con la extensión sqlite-vec para búsqueda vectorial.
        También utiliza FTS5 para búsqueda por palabras clave.
        Esto permite una búsqueda híbrida eficiente y privada.

        Los especialistas pueden ser delegados por el Master Orchestrator.
        Cada especialista tiene habilidades únicas.
        El sistema es altamente modular y escalable.
        """

        print("\n📝 Ingesting text...")
        new_chunks = await pipeline.process_text(chat_id, text)
        print(f"✅ Ingested {new_chunks} new chunks")

        # 3. Verify counts in DB
        db = await store.get_db()
        async with db.execute(
            "SELECT COUNT(*) FROM memories WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            print(f"📊 Memories in DB: {count}")
            assert count == new_chunks

        async with db.execute("SELECT COUNT(*) FROM memory_vectors") as cursor:
            v_count = (await cursor.fetchone())[0]
            print(f"📊 Vectors in DB: {v_count}")
            assert v_count >= count

        # 4. Test Deduplication
        print("\n🔄 Testing deduplication (ingesting same text again)...")
        duplicated_chunks = await pipeline.process_text(chat_id, text)
        print(f"✅ Ingested {duplicated_chunks} chunks (should be 0)")
        assert duplicated_chunks == 0

        print("\n" + "=" * 50)
        print("✅ PHASE 2 VERIFICATION SUCCESSFUL!")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await store.disconnect()


if __name__ == "__main__":
    asyncio.run(test_ingestion())
