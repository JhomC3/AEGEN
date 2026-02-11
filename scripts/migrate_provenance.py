#!/usr/bin/env python3
# scripts/migrate_provenance.py
"""
One-time migration script for AEGEN database.

Fixes:
1. Namespace contamination: personal files indexed under 'global' namespace
2. Missing provenance columns on existing data

Usage: python -m scripts.migrate_provenance
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.migration import apply_migrations
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migration")


async def main():
    store = SQLiteStore(settings.SQLITE_DB_PATH)
    # Ensure tables and migrations are applied
    await store.init_db(settings.SQLITE_SCHEMA_PATH)
    await apply_migrations(store)

    db = await store.get_db()

    # 1. Identify contaminated global memories (personal files in global namespace)
    logger.info("=== Step 1: Cleaning namespace contamination ===")
    async with db.execute(
        "SELECT id, content_hash, metadata FROM memories WHERE namespace = 'global'"
    ) as cursor:
        global_rows = await cursor.fetchall()

    contaminated_ids = []
    import json

    for row in global_rows:
        meta = json.loads(row[2]) if row[2] else {}
        source = str(meta.get("source", ""))
        # Personal files often have user IDs in the source name or specific keywords
        if (
            any(char.isdigit() for char in source)
            or "buffer" in source
            or "profile" in source
            or "vault" in source
            or "summary" in source
            or "knowledge" in source
        ):
            # We filter out pure psychological core docs if they happen to have numbers (unlikely)
            if "CORE" in source or "Unified Protocol" in source:
                continue
            contaminated_ids.append(row[0])

    if contaminated_ids:
        logger.info(f"Found {len(contaminated_ids)} contaminated global memories")
        placeholders = ",".join(["?"] * len(contaminated_ids))
        await db.execute(
            f"UPDATE memories SET is_active = 0, sensitivity = 'high' WHERE id IN ({placeholders})",
            contaminated_ids,
        )
        await db.commit()
        logger.info(f"Deactivated {len(contaminated_ids)} contaminated memories")
    else:
        logger.info("No namespace contamination found")

    # 2. Set provenance defaults on existing data
    logger.info("=== Step 2: Setting provenance defaults ===")
    # Note: SQLite doesn't support UPDATE ... WHERE column IS NULL if the column was added with NOT NULL DEFAULT
    # But for safety we check both
    await db.execute(
        "UPDATE memories SET source_type = 'explicit', confidence = 1.0, sensitivity = 'low' "
        "WHERE source_type = 'explicit' AND evidence IS NULL"
    )
    await db.commit()

    # Summary
    async with db.execute(
        "SELECT namespace, is_active, COUNT(*) FROM memories GROUP BY namespace, is_active"
    ) as cursor:
        logger.info("=== Final State ===")
        for row in await cursor.fetchall():
            status = "active" if row[1] else "inactive"
            logger.info(f"  {row[0]} ({status}): {row[2]} memories")

    await store.disconnect()
    logger.info("Migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
