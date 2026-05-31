# src/memory/knowledge_tracker.py
"""
Tracker de archivos de conocimiento global.

Gestiona la tabla knowledge_files para trazabilidad completa
de la ingesta de PDFs, MD y TXT en storage/knowledge/.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from src.memory.schemas.knowledge import (
    KnowledgeChunker,
    KnowledgeFile,
    KnowledgeStatus,
)
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class KnowledgeTracker:
    """
    Persiste el estado de cada archivo de conocimiento en SQLite.

    Responsabilidades:
    - Registrar archivos nuevos (status=pending)
    - Actualizar estado (ingesting, done, failed)
    - Listar todos los archivos
    - Buscar por filename o hash
    - Eliminar registros
    """

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    async def register_file(
        self,
        filename: str,
        file_hash: str,
        file_size: int,
        chunker: KnowledgeChunker = KnowledgeChunker.SEMANTIC,
    ) -> KnowledgeFile:
        """Registra un archivo nuevo con status=pending."""
        now = datetime.now(UTC)
        db = await self.store.get_db()
        cursor = await db.execute(
            """
            INSERT INTO knowledge_files
            (filename, file_hash, file_size, status, chunker, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                file_hash,
                file_size,
                KnowledgeStatus.PENDING.value,
                chunker.value,
                now.isoformat(),
            ),
        )
        await db.commit()
        file_id = cursor.lastrowid or 0

        logger.info(
            "[TRACKER] Registrado: %s (id=%d, hash=%s...)",
            filename,
            file_id,
            file_hash[:12],
        )
        return KnowledgeFile(
            id=file_id,
            filename=filename,
            file_hash=file_hash,
            file_size=file_size,
            status=KnowledgeStatus.PENDING,
            chunker=chunker,
            updated_at=now,
        )

    async def update_status(
        self,
        file_id: int,
        status: KnowledgeStatus,
        chunks_count: int = 0,
        chunks_ids: list[int] | None = None,
        error_message: str | None = None,
    ) -> KnowledgeFile | None:
        """Actualiza el estado de un archivo."""
        now = datetime.now(UTC)
        db = await self.store.get_db()

        ids_json = json.dumps(chunks_ids or [])
        await db.execute(
            """
            UPDATE knowledge_files
            SET status = ?, chunks_count = ?, chunks_ids = ?,
                ingested_at = ?, updated_at = ?, error_message = ?
            WHERE id = ?
            """,
            (
                status.value,
                chunks_count,
                ids_json,
                now.isoformat() if status == KnowledgeStatus.DONE else None,
                now.isoformat(),
                error_message,
                file_id,
            ),
        )
        await db.commit()

        return await self.get_by_id(file_id)

    async def get_by_id(self, file_id: int) -> KnowledgeFile | None:
        """Busca archivo por ID."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT * FROM knowledge_files WHERE id = ?", (file_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_model(row) if row else None

    async def get_by_filename(self, filename: str) -> KnowledgeFile | None:
        """Busca archivo por nombre."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT * FROM knowledge_files WHERE filename = ?", (filename,)
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_model(row) if row else None

    async def get_by_hash(self, file_hash: str) -> KnowledgeFile | None:
        """Busca archivo por hash (dedup)."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT * FROM knowledge_files WHERE file_hash = ?", (file_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_model(row) if row else None

    async def list_all(self) -> list[KnowledgeFile]:
        """Lista todos los archivos registrados."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT * FROM knowledge_files ORDER BY filename"
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    async def delete(self, file_id: int) -> bool:
        """Elimina un registro del tracker."""
        db = await self.store.get_db()
        cursor = await db.execute(
            "DELETE FROM knowledge_files WHERE id = ?", (file_id,)
        )
        await db.commit()
        return bool(cursor.rowcount > 0)

    async def get_total_chunks(self) -> int:
        """Retorna el total de chunks registrados."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT COALESCE(SUM(chunks_count), 0) "
            "FROM knowledge_files WHERE status = 'done'"
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    def _row_to_model(self, row: object) -> KnowledgeFile:
        """Convierte una fila de SQLite a KnowledgeFile."""
        r: tuple = row  # type: ignore[assignment]
        chunks_ids: list[int] = []
        try:
            raw = r[7]  # chunks_ids column (JSON string)
            if raw:
                chunks_ids = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

        return KnowledgeFile(
            id=r[0],
            filename=r[1],
            file_hash=r[2],
            file_size=r[3],
            status=KnowledgeStatus(r[4]),
            chunker=KnowledgeChunker(r[5]),
            chunks_count=int(r[6]) if r[6] else 0,
            chunks_ids=chunks_ids,
            ingested_at=r[8] if r[8] else None,
            updated_at=r[9] if r[9] else datetime.now(),
            error_message=r[10] if r[10] else None,
        )
