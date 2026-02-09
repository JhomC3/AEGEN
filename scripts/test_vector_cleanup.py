#!/usr/bin/env python3
"""
Test script to verify the automatic vector cleanup trigger.

This script tests that when a memory is deleted, the cascade trigger
properly cleans up:
1. The FTS5 index entry (memories_fts)
2. The vector mapping entry (vector_memory_map)
3. The physical vector data (memory_vectors) ← NEW TRIGGER

Without the cleanup_vector_on_map_delete trigger, step 3 would leave
orphaned vectors consuming disk space.
"""

import asyncio
import logging
import struct
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cleanup_cascade():
    """Test that deleting a memory cascades to clean up the vector."""

    print("\n" + "=" * 70)
    print("🧪 TEST: Vector Cleanup Trigger")
    print("=" * 70 + "\n")

    store = SQLiteStore(settings.SQLITE_DB_PATH)

    try:
        # Initialize DB
        await store.init_db(settings.SQLITE_SCHEMA_PATH)
        db = await store.get_db()

        # Step 1: Insert a test memory
        print("📝 Step 1: Inserting test memory...")
        await db.execute(
            """
            INSERT INTO memories (chat_id, namespace, content, content_hash, memory_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("test_chat", "user", "Test memory content", "hash_123", "fact"),
        )
        await db.commit()

        # Get the memory ID
        async with db.execute(
            "SELECT id FROM memories WHERE content_hash = 'hash_123'"
        ) as cursor:
            row = await cursor.fetchone()
            memory_id = row[0]

        print(f"   ✅ Memory inserted with ID: {memory_id}")

        # Step 2: Create a fake vector (768 dimensions, all zeros for testing)
        print("\n🧮 Step 2: Inserting test vector...")

        # Create a 768-dimension zero vector
        vector = [0.0] * 768

        # Insert vector using sqlite-vec syntax
        await db.execute(
            "INSERT INTO memory_vectors(embedding) VALUES (?)",
            (struct.pack(f"{len(vector)}f", *vector),),
        )
        await db.commit()

        # Get the vector rowid
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            row = await cursor.fetchone()
            vector_id = row[0]

        print(f"   ✅ Vector inserted with rowid: {vector_id}")

        # Step 3: Link vector to memory
        print("\n🔗 Step 3: Linking vector to memory...")
        await db.execute(
            "INSERT INTO vector_memory_map (vector_id, memory_id) VALUES (?, ?)",
            (vector_id, memory_id),
        )
        await db.commit()
        print(f"   ✅ Link created: vector {vector_id} ↔ memory {memory_id}")

        # Verify everything exists
        print("\n📊 Pre-deletion state:")

        async with db.execute(
            "SELECT COUNT(*) FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            print(f"   • memories table: {count} record(s)")

        async with db.execute(
            "SELECT COUNT(*) FROM vector_memory_map WHERE vector_id = ?", (vector_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            print(f"   • vector_memory_map: {count} record(s)")

        async with db.execute(
            "SELECT COUNT(*) FROM memory_vectors WHERE rowid = ?", (vector_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            print(f"   • memory_vectors: {count} record(s)")

        # Step 4: DELETE THE MEMORY (trigger the cascade)
        print("\n🗑️  Step 4: Deleting memory (triggering cascade)...")
        await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await db.commit()
        print("   ✅ Memory deleted")

        # Step 5: Verify cascade cleanup
        print("\n🔍 Step 5: Verifying cleanup cascade...")

        # Check memories table (should be empty)
        async with db.execute(
            "SELECT COUNT(*) FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 0, "❌ Memory not deleted!"
            print(f"   ✅ memories table cleaned: {count} record(s)")

        # Check FTS5 index (should be cleaned by memories_ad trigger)
        async with db.execute(
            "SELECT COUNT(*) FROM memories_fts WHERE rowid = ?", (memory_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 0, "❌ FTS5 index not cleaned!"
            print(f"   ✅ FTS5 index cleaned: {count} record(s)")

        # Check vector_memory_map (should be cleaned by ON DELETE CASCADE)
        async with db.execute(
            "SELECT COUNT(*) FROM vector_memory_map WHERE vector_id = ?", (vector_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 0, "❌ Vector map not cleaned!"
            print(f"   ✅ vector_memory_map cleaned: {count} record(s)")

        # Check memory_vectors (should be cleaned by cleanup_vector_on_map_delete trigger)
        async with db.execute(
            "SELECT COUNT(*) FROM memory_vectors WHERE rowid = ?", (vector_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            assert (
                count == 0
            ), f"❌ CRITICAL: Physical vector NOT cleaned! Found {count} orphaned vector(s)"
            print(f"   ✅ memory_vectors cleaned: {count} record(s) ← TRIGGER WORKS!")

        print("\n" + "=" * 70)
        print("✅ TEST PASSED: Vector cleanup trigger works correctly!")
        print("=" * 70)
        print("\n🎉 No orphaned vectors! Disk space is properly reclaimed.\n")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        logger.error(f"❌ Error during test: {e}", exc_info=True)
        return False
    finally:
        await store.disconnect()


if __name__ == "__main__":
    success = asyncio.run(test_cleanup_cascade())
    sys.exit(0 if success else 1)
