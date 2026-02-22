# src/memory/hybrid_search.py
# ruff: noqa: S608
import asyncio
import json
import logging
from typing import Any

from src.memory.embeddings import EmbeddingService
from src.memory.keyword_search import KeywordSearch
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_search import VectorSearch

logger = logging.getLogger(__name__)


class HybridSearch:
    """Búsqueda híbrida."""

    def __init__(self, store: SQLiteStore) -> None:
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
        vw: float = 0.7,
        kw: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Búsqueda principal."""
        emb = await self.embedding_service.embed_query(query)
        v_res, k_res = await asyncio.gather(
            self.vector_search.search(emb, limit * 2, chat_id, namespace),
            self.keyword_search.search(query, limit * 2, chat_id, namespace),
        )
        rrf = self._merge_rrf(v_res, k_res, rrf_k, vw, kw)
        sorted_ids = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:limit]
        if not sorted_ids:
            return []
        return await self._hydrate([it[0] for it in sorted_ids], sorted_ids)

    async def search_by_type(
        self,
        memory_type: str,
        limit: int = 10,
        chat_id: str | None = None,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """Búsqueda por tipo."""
        db = await self.store.get_db()
        sql = (
            "SELECT id, content, memory_type, metadata, chat_id "
            "FROM memories WHERE memory_type = ? AND is_active = 1"
        )
        params: list[Any] = [memory_type]
        if chat_id:
            sql += " AND chat_id = ?"
            params.append(chat_id)
        if namespace:
            sql += " AND namespace = ?"
            params.append(namespace)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with db.execute(sql, params) as cursor:
            return [
                {
                    "id": r[0],
                    "content": r[1],
                    "memory_type": r[2],
                    "metadata": json.loads(r[3]),
                    "chat_id": r[4],
                }
                for r in await cursor.fetchall()
            ]

    def _merge_rrf(
        self, v: list, k: list, k_val: int, vw: float, kw: float
    ) -> dict[int, float]:
        """Algoritmo RRF."""
        scores: dict[int, float] = {}
        for r, (mid, _) in enumerate(v, 1):
            scores[mid] = scores.get(mid, 0.0) + (vw * (1.0 / (k_val + r)))
        for r, (mid, _) in enumerate(k, 1):
            scores[mid] = scores.get(mid, 0.0) + (kw * (1.0 / (k_val + r)))
        return scores

    async def _hydrate(
        self, ids: list[int], sorted_ids: list[tuple[int, float]]
    ) -> list[dict[str, Any]]:
        """Carga de SQLite."""
        db = await self.store.get_db()
        m = ",".join(["?"] * len(ids))
        sql = (
            "SELECT id, chat_id, content, memory_type, metadata "
            f"FROM memories WHERE id IN ({m}) AND is_active = 1"
        )  # noqa: S608
        res = []
        async with db.execute(sql, ids) as cursor:
            rows = {r["id"]: r for r in await cursor.fetchall()}
            for mid, score in sorted_ids:
                if mid in rows:
                    r = rows[mid]
                    res.append({
                        "id": r["id"],
                        "content": r["content"],
                        "memory_type": r["memory_type"],
                        "metadata": json.loads(r["metadata"]),
                        "score": score,
                        "chat_id": r["chat_id"],
                    })
        return res
