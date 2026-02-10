# src/memory/vector_search.py
"""
Vector search module using sqlite-vec.

Implements K-Nearest Neighbors (KNN) search for semantic retrieval.
"""

import logging
import struct
from typing import Any

from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class VectorSearch:
    """
    Gestor de búsqueda vectorial KNN.
    """

    def __init__(self, store: SQLiteStore):
        self.store = store

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
    ) -> list[tuple[int, float]]:
        """
        Realiza una búsqueda KNN en la tabla de vectores.

        Args:
            query_embedding: Vector de la consulta (768 dims)
            limit: Número máximo de resultados
            chat_id: Opcional, filtrar por chat
            namespace: Opcional, filtrar por namespace

        Returns:
            Lista de tuplas (memory_id, distance)
        """
        db = await self.store.get_db()
        vector_blob = struct.pack(f"{len(query_embedding)}f", *query_embedding)

        # SQL para búsqueda vectorial con sqlite-vec
        # vec_distance_L2 o vec_distance_cosine
        # Usamos rowid para unir con el mapa de memorias

        query = """
            SELECT
                m.memory_id,
                v.distance
            FROM memory_vectors v
            JOIN vector_memory_map m ON v.rowid = m.vector_id
            JOIN memories mem ON m.memory_id = mem.id
            WHERE v.embedding MATCH ?
            AND k = ?
        """
        params: list[Any] = [vector_blob, limit]

        if chat_id:
            query += " AND mem.chat_id = ?"
            params.append(chat_id)

        if namespace:
            query += " AND mem.namespace = ?"
            params.append(namespace)

        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                # sqlite-vec devuelve la distancia en la columna 'distance'
                return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
