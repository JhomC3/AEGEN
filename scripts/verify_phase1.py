import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore

# Configurar logging básico
logging.basicConfig(level=logging.INFO)


async def test():
    print(f"Testing database at: {settings.SQLITE_DB_PATH}")
    store = SQLiteStore(settings.SQLITE_DB_PATH)

    try:
        # 1. Init DB (executes schema)
        await store.init_db(settings.SQLITE_SCHEMA_PATH)
        print("✅ Schema initialized")

        db = await store.get_db()

        # 2. Check FTS5
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_fts'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                print(f"✅ FTS5 Table found: {row['name']}")
            else:
                print("❌ FTS5 Table NOT found")

        # 3. Check sqlite-vec
        async with db.execute("SELECT vec_version()") as cursor:
            row = await cursor.fetchone()
            print(f"✅ sqlite-vec loaded: version {row[0]}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await store.disconnect()


if __name__ == "__main__":
    asyncio.run(test())
