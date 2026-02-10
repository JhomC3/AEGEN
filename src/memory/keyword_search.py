# src/memory/keyword_search.py
"""
Keyword search module using SQLite FTS5.

Implements full-text search for exact and prefix matching.
"""

import logging
from typing import Any

from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class KeywordSearch:
    """
    Gestor de búsqueda por palabras clave (FTS5).
    """

    def __init__(self, store: SQLiteStore):
        self.store = store

    async def search(
        self,
        query_text: str,
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
    ) -> list[tuple[int, float]]:
        """
        Realiza una búsqueda FTS5.

        Args:
            query_text: Texto a buscar
            limit: Número máximo de resultados
            chat_id: Opcional, filtrar por chat
            namespace: Opcional, filtrar por namespace

        Returns:
            Lista de tuplas (memory_id, score) - BM25 score (menor es mejor en FTS5 rank)
        """
        if not query_text or not query_text.strip():
            return []

        db = await self.store.get_db()

        # SQL para FTS5
        # rank es el score BM25 (negativo por defecto, más negativo es mejor)
        # Usamos rowid para identificar la memoria

        query = """
            SELECT
                rowid,
                rank
            FROM memories_fts
            WHERE memories_fts MATCH ?
        """
        params: list[Any] = [query_text]

        # Filtros adicionales requieren JOIN con memories si no están en la tabla FTS
        # Como no están en la tabla virtual, unimos:

        query = """
            SELECT
                m.id,
                f.rank
            FROM memories_fts f
            JOIN memories m ON f.rowid = m.id
            WHERE f.content MATCH ?
        """

        if chat_id:
            query += " AND m.chat_id = ?"
            params.append(chat_id)

        if namespace:
            query += " AND m.namespace = ?"
            params.append(namespace)

        query += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
