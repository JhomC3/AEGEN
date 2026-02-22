import json
import logging
import sqlite3
import struct
from typing import Any, cast

import aiosqlite

logger = logging.getLogger(__name__)


class MemoryRepository:
    """Repositorio de memorias."""

    def __init__(self, store: Any) -> None:
        self.store = store

    async def get_db(self) -> aiosqlite.Connection:
        return cast(aiosqlite.Connection, await self.store.get_db())

    async def insert_memory(
        self,
        chat_id: str,
        content: str,
        content_hash: str,
        memory_type: str,
        namespace: str = "user",
        metadata: dict[str, Any] | None = None,
        source_type: str = "explicit",
        confidence: float = 1.0,
        sensitivity: str = "low",
        evidence: str | None = None,
    ) -> int:
        db = await self.get_db()
        metadata_json = json.dumps(metadata or {})
        try:
            cursor = await db.execute(
                """
                INSERT INTO memories
                    (chat_id, namespace, content, content_hash, memory_type,
                     metadata, source_type, confidence, sensitivity, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    namespace,
                    content,
                    content_hash,
                    memory_type,
                    metadata_json,
                    source_type,
                    confidence,
                    sensitivity,
                    evidence,
                ),
            )
            mid = cursor.lastrowid
            await db.commit()
            return int(mid) if mid is not None else -1
        except sqlite3.IntegrityError:
            async with db.execute(
                "SELECT id FROM memories WHERE content_hash = ?", (content_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row else -1
        except Exception as e:
            logger.error("Insert error: %s", e)
            await db.rollback()
            raise

    async def get_memory_stats(self, chat_id: str) -> dict[str, Any]:
        db = await self.get_db()
        stats: dict[str, Any] = {"total": 0, "by_type": {}, "by_sensitivity": {}}
        try:
            async with db.execute(
                "SELECT memory_type, sensitivity, COUNT(*) FROM memories "
                "WHERE chat_id = ? AND is_active = 1 GROUP BY 1, 2",
                (chat_id,),
            ) as cursor:
                for row in await cursor.fetchall():
                    mtype, sens, cnt = row[0], row[1] or "low", row[2]
                    stats["by_type"][mtype] = stats["by_type"].get(mtype, 0) + cnt
                    stats["by_sensitivity"][sens] = (
                        stats["by_sensitivity"].get(sens, 0) + cnt
                    )
                    stats["total"] += cnt
        except Exception as e:
            logger.error("Stats error: %s", e)
        return stats

    async def insert_vector(self, mid: int, embedding: list[float]) -> int:
        db = await self.get_db()
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        try:
            # 1. Insert into virtual table memory_vectors to get the vector rowid
            cursor = await db.execute(
                "INSERT INTO memory_vectors (embedding) VALUES (?)",
                (blob,),
            )
            vec_id = cursor.lastrowid

            # 2. Map the vector rowid to the memory id
            await db.execute(
                "INSERT INTO vector_memory_map (vector_id, memory_id) VALUES (?, ?)",
                (vec_id, mid),
            )

            await db.commit()
            return mid
        except Exception as e:
            logger.error("Vector error: %s", e)
            await db.rollback()
            raise

    async def hash_exists(self, h: str) -> bool:
        db = await self.get_db()
        async with db.execute(
            "SELECT 1 FROM memories WHERE content_hash = ?", (h,)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def soft_delete_memories(self, ids: list[int]) -> int:
        if not ids:
            return 0
        db = await self.get_db()
        marks = ",".join(["?"] * len(ids))
        try:
            sql = f"UPDATE memories SET is_active = 0 WHERE id IN ({marks})"  # noqa: S608
            cursor = await db.execute(sql, ids)
            await db.commit()
            return int(cursor.rowcount)
        except Exception as e:
            logger.error("Delete error: %s", e)
            await db.rollback()
            return 0

    async def delete_memories_by_filename(self, f: str, ns: str = "global") -> int:
        db = await self.get_db()
        try:
            sql = (
                "UPDATE memories SET is_active = 0 WHERE namespace = ? "
                "AND json_extract(metadata, '$.filename') = ?"
            )
            cursor = await db.execute(sql, (ns, f))
            await db.commit()
            return int(cursor.rowcount)
        except Exception as e:
            logger.error("Delete file error: %s", e)
            await db.rollback()
            return 0
