# src/memory/keyword_search.py
"""
Keyword search module using SQLite FTS5.

Implements full-text search for exact and prefix matching.
"""

import logging
import re
from typing import Any

from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class KeywordSearch:
    """
    Gestor de búsqueda por palabras clave (FTS5).
    """

    def __init__(self, store: SQLiteStore):
        self.store = store

    @staticmethod
    def _sanitize_fts5_query(query: str) -> str:
        """
        Escapa caracteres especiales para FTS5 MATCH.
        Enfocado en robustez para consultas de chat.
        """
        # 1. Eliminar caracteres que FTS5 interpreta como operadores
        # Mantenemos letras, números y espacios.
        sanitized = re.sub(r"[^\w\s]", " ", query, flags=re.UNICODE)

        # 2. Colapsar espacios múltiples
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        if not sanitized:
            return ""

        # 3. Envolver cada término en comillas para búsqueda literal.
        # SQLite FTS5 maneja bien "termino1" "termino2" como AND implícito.
        terms = [f'"{t}"' for t in sanitized.split() if len(t) >= 2]

        if not terms:
            return ""

        # Unimos con espacios (AND implícito en FTS5).
        return " ".join(terms)

    async def search(
        self,
        query_text: str,
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
    ) -> list[tuple[int, float]]:
        """
        Realiza una búsqueda FTS5.
        """
        if not query_text or not query_text.strip():
            return []

        # Sanitizar la entrada del usuario antes de pasarla a MATCH
        sanitized_query = self._sanitize_fts5_query(query_text)
        if not sanitized_query:
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
        params: list[Any] = [sanitized_query]

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
