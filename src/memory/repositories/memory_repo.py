import json
import logging
import sqlite3
import struct
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class MemoryRepository:
    """
    Repositorio para operaciones de memoria en SQLite.
    """

    def __init__(self, store: Any):
        self.store = store

    async def get_db(self) -> aiosqlite.Connection:
        return await self.store.get_db()

    async def insert_memory(
        self,
        chat_id: str,
        content: str,
        content_hash: str,
        memory_type: str,
        namespace: str = "user",
        metadata: dict | None = None,
        source_type: str = "explicit",
        confidence: float = 1.0,
        sensitivity: str = "low",
        evidence: str | None = None,
    ) -> int:
        """
        Inserta una memoria con metadatos de provenance.
        Retorna el ID de la memoria insertada.
        """
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
            memory_id = cursor.lastrowid
            await db.commit()
            return memory_id if memory_id is not None else -1
        except sqlite3.IntegrityError:
            # Probablemente duplicado por hash
            logger.debug(f"Memory with hash {content_hash} already exists.")
            async with db.execute(
                "SELECT id FROM memories WHERE content_hash = ?", (content_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else -1
        except Exception as e:
            logger.error(f"Error inserting memory: {e}")
            await db.rollback()
            raise

    async def insert_vector(self, memory_id: int, embedding: list[float]) -> int:
        """
        Inserta un vector y lo vincula con una memoria.
        """
        db = await self.get_db()
        vector_blob = struct.pack(f"{len(embedding)}f", *embedding)

        try:
            # 1. Insertar en tabla vectorial
            cursor = await db.execute(
                "INSERT INTO memory_vectors(embedding) VALUES (?)", (vector_blob,)
            )
            vector_id = cursor.lastrowid

            # 2. Vincular en tabla de mapeo
            await db.execute(
                "INSERT INTO vector_memory_map (vector_id, memory_id) VALUES (?, ?)",
                (vector_id, memory_id),
            )
            await db.commit()
            return vector_id if vector_id is not None else -1
        except Exception as e:
            logger.error(f"Error inserting vector: {e}")
            await db.rollback()
            raise

    async def hash_exists(self, content_hash: str) -> bool:
        """Verifica si un hash de contenido ya existe en la DB."""
        db = await self.get_db()
        async with db.execute(
            "SELECT 1 FROM memories WHERE content_hash = ?", (content_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

    async def soft_delete_memories(self, memory_ids: list[int]) -> int:
        """Marca memorias como inactivas (borrado suave). Retorna la cuenta actualizada."""
        if not memory_ids:
            return 0
        db = await self.get_db()
        placeholders = ",".join(["?"] * len(memory_ids))
        try:
            cursor = await db.execute(
                f"UPDATE memories SET is_active = 0 WHERE id IN ({placeholders})",  # nosec B608
                memory_ids,
            )
            await db.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error en soft_delete_memories: {e}")
            await db.rollback()
            return 0

    async def get_memory_stats(self, chat_id: str) -> dict:
        """Retorna estadísticas de memoria para un usuario."""
        db = await self.get_db()
        stats: dict = {"total": 0, "by_type": {}, "by_sensitivity": {}}
        try:
            async with db.execute(
                "SELECT memory_type, sensitivity, COUNT(*) as cnt "
                "FROM memories WHERE chat_id = ? AND is_active = 1 "
                "GROUP BY memory_type, sensitivity",
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
            logger.error(f"Error in get_memory_stats: {e}")
        return stats
