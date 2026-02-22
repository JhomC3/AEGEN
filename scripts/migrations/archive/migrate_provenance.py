import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")


async def main() -> None:
    store = SQLiteStore(settings.SQLITE_DB_PATH)
    db = await store.get_db()
    async with db.execute("SELECT id, metadata FROM memories") as cursor:
        rows = await cursor.fetchall()
    for row in rows:
        meta = json.loads(row[1]) if row[1] else {}
        if "PDF" in str(meta.get("source")):
            await db.execute(
                "UPDATE memories SET is_active = 0 WHERE id = ?", (row[0],)
            )
    await db.commit()
    logger.info("Migration complete")


if __name__ == "__main__":
    asyncio.run(main())
