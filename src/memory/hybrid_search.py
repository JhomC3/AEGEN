# src/memory/hybrid_search.py
"""
Hybrid search module combining vector and keyword results.

Uses Reciprocal Rank Fusion (RRF) to rank documents from multiple sources.
"""

import logging
from typing import Any

from src.memory.embeddings import EmbeddingService
from src.memory.keyword_search import KeywordSearch
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_search import VectorSearch

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Gestor de búsqueda híbrida (Vector + Keyword).
    """

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.vector_search = VectorSearch(store)
        self.keyword_search = KeywordSearch(store)
        self.embedding_service = EmbeddingService()

    async def search(
        self,
        query: str,
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
        rrf_k: int = 60,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Realiza una búsqueda híbrida y combina resultados con RRF.

        Args:
            query: Consulta en texto
            limit: Número máximo de resultados finales
            chat_id: Opcional, filtrar por chat
            namespace: Opcional, filtrar por namespace
            rrf_k: Constante para suavizar el ranking RRF
            vector_weight: Peso para los resultados vectoriales
            keyword_weight: Peso para los resultados por keyword

        Returns:
            Lista de diccionarios con contenido de memoria y metadatos
        """
        # 1. Obtener embedding para la búsqueda vectorial
        query_embedding = await self.embedding_service.embed_query(query)

        # 2. Ejecutar búsquedas en paralelo (si fuera posible, aquí secuencial por simplicidad)
        vector_results = await self.vector_search.search(
            query_embedding, limit=limit * 2, chat_id=chat_id, namespace=namespace
        )
        keyword_results = await self.keyword_search.search(
            query, limit=limit * 2, chat_id=chat_id, namespace=namespace
        )

        # 3. Combinar resultados con RRF
        # rrf_scores[memory_id] = score
        rrf_scores: dict[int, float] = {}

        # Procesar resultados vectoriales
        for rank, (memory_id, _) in enumerate(vector_results, 1):
            rrf_scores[memory_id] = rrf_scores.get(memory_id, 0.0) + (
                vector_weight * (1.0 / (rrf_k + rank))
            )

        # Procesar resultados de palabras clave
        for rank, (memory_id, _) in enumerate(keyword_results, 1):
            rrf_scores[memory_id] = rrf_scores.get(memory_id, 0.0) + (
                keyword_weight * (1.0 / (rrf_k + rank))
            )

        # 4. Ordenar por score y limitar
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]

        if not sorted_ids:
            return []

        # 5. Hidratar resultados con el contenido de la DB
        result_ids = [item[0] for item in sorted_ids]
        db = await self.store.get_db()

        # SQL para hidratar
        placeholders = ",".join(["?"] * len(result_ids))
        query_sql = f"""
            SELECT id, chat_id, content, memory_type, metadata, created_at
            FROM memories
            WHERE id IN ({placeholders})
        """

        hydrated_results = []
        try:
            async with db.execute(query_sql, result_ids) as cursor:
                rows = await cursor.fetchall()
                # Crear mapeo para mantener el orden de RRF
                rows_map = {row["id"]: row for row in rows}

                import json

                for memory_id, score in sorted_ids:
                    if memory_id in rows_map:
                        row = rows_map[memory_id]
                        hydrated_results.append({
                            "id": row["id"],
                            "content": row["content"],
                            "memory_type": row["memory_type"],
                            "metadata": json.loads(row["metadata"])
                            if isinstance(row["metadata"], str)
                            else row["metadata"],
                            "score": score,
                            "chat_id": row["chat_id"],
                            "created_at": row["created_at"],
                        })
        except Exception as e:
            logger.error(f"Error hydrating hybrid search results: {e}")

        return hydrated_results

    async def search_by_type(
        self,
        memory_type: str,
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """
        Recupera memorias filtrando solo por tipo (sin búsqueda semántica).
        """
        db = await self.store.get_db()
        query = "SELECT * FROM memories WHERE memory_type = ?"
        params: list[Any] = [memory_type]

        if chat_id:
            query += " AND chat_id = ?"
            params.append(chat_id)
        if namespace:
            query += " AND namespace = ?"
            params.append(namespace)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = []
        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                import json

                for row in rows:
                    results.append({
                        "id": row["id"],
                        "content": row["content"],
                        "memory_type": row["memory_type"],
                        "metadata": json.loads(row["metadata"])
                        if isinstance(row["metadata"], str)
                        else row["metadata"],
                        "chat_id": row["chat_id"],
                        "created_at": row["created_at"],
                    })
        except Exception as e:
            logger.error(f"Error in search_by_type: {e}")

        return results
