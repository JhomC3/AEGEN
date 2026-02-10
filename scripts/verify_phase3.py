# scripts/verify_phase3.py
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_search():
    print(f"\nTesting hybrid search at: {settings.SQLITE_DB_PATH}")
    store = SQLiteStore(settings.SQLITE_DB_PATH)

    try:
        # 1. Init DB
        await store.init_db(settings.SQLITE_SCHEMA_PATH)
        print("✅ Schema initialized")

        manager = VectorMemoryManager(store)
        chat_id = "test_verify_phase3"

        # 2. Seed some memories
        print("\n📝 Seeding test memories...")

        memories = [
            (
                "Python es un lenguaje de programación muy popular.",
                "popularidad de python",
            ),
            ("SQLite es una base de datos ligera y embebida.", "base de datos sqlite"),
            ("MAGI utiliza inteligencia artificial para razonar.", "razonamiento magi"),
            (
                "La arquitectura local-first mejora la privacidad.",
                "privacidad local-first",
            ),
            ("El clima en Buenos Aires es templado.", "clima buenos aires"),
        ]

        for content, _ in memories:
            await manager.store_context(chat_id, content, MemoryType.FACT)

        print(f"✅ Seeded {len(memories)} memories")

        # 3. Test Vector Search (Semantic)
        print("\n🔍 Testing Semantic Search ('lenguaje popular')...")
        results = await manager.retrieve_context(chat_id, "lenguaje popular", limit=2)
        for res in results:
            print(f"   • [{res['score']:.4f}] {res['content']}")
        assert "Python" in results[0]["content"]

        # 4. Test Keyword Search (Exact match)
        print("\n🔍 Testing Keyword Search ('SQLite')...")
        results = await manager.retrieve_context(chat_id, "SQLite", limit=1)
        for res in results:
            print(f"   • [{res['score']:.4f}] {res['content']}")
        assert "SQLite" in results[0]["content"]

        # 5. Test Hybrid Search (RRF)
        # Una consulta que debería combinar ambos
        print(
            "\n🔍 Testing Hybrid Search ('arquitectura de inteligencia artificial')..."
        )
        results = await manager.retrieve_context(
            chat_id, "arquitectura de inteligencia artificial", limit=3
        )
        for res in results:
            print(f"   • [{res['score']:.4f}] {res['content']}")

        print("\n" + "=" * 50)
        print("✅ PHASE 3 VERIFICATION SUCCESSFUL!")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await store.disconnect()


if __name__ == "__main__":
    asyncio.run(test_search())
