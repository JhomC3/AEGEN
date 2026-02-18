import logging
from enum import Enum
from typing import Any

from src.core.config import settings
from src.memory.hybrid_search import HybridSearch
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    DOCUMENT = "document"


class VectorMemoryManager:
    """Gestor de memoria de alto nivel."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self.store = store or SQLiteStore(settings.SQLITE_DB_PATH)
        self.pipeline = IngestionPipeline(self.store)
        self.hybrid_search = HybridSearch(self.store)
        logger.info("VectorMemoryManager initialized")

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        context_type: MemoryType | None = None,
        limit: int = 5,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """Recupera memorias relevantes."""
        import time

        start = time.monotonic()
        results = await self.hybrid_search.search(
            query=query, limit=limit, chat_id=user_id, namespace=namespace
        )
        elapsed = (time.monotonic() - start) * 1000
        self._log_trace(user_id, namespace, query, results, elapsed)
        if context_type:
            results = [r for r in results if r["memory_type"] == context_type.value]
        return results

    def _log_trace(
        self, uid: str, ns: str, q: str, res: list[dict[str, Any]], ms: float
    ) -> None:
        """Emite traza RAG."""
        frags = [
            {
                "id": r["id"],
                "score": round(r.get("score", 0), 4),
                "source": r.get("metadata", {}).get("filename", "?"),
                "preview": r["content"][:100],
            }
            for r in res
        ]
        logger.info(
            "[RAG] %s: %d frags, %.0fms | q='%s...'",
            ns,
            len(res),
            ms,
            q[:50],
            extra={
                "event": "rag_retrieval",
                "user_id": uid,
                "latency": round(ms, 1),
                "fragments": frags,
            },
        )

    async def store_context(
        self,
        user_id: str,
        content: str,
        context_type: MemoryType = MemoryType.CONVERSATION,
        metadata: dict[str, Any] | None = None,
        namespace: str = "user",
    ) -> int:
        """Almacena contenido."""
        return await self.pipeline.process_text(
            chat_id=user_id,
            text=content,
            memory_type=context_type.value,
            namespace=namespace,
            metadata=metadata,
        )

    async def delete_file_knowledge(
        self, filename: str, namespace: str = "global"
    ) -> int:
        """Borrado suave por filename."""
        count = await self.store.delete_memories_by_filename(filename, namespace)
        if count > 0:
            logger.info("Deactivated %d frags of %s", count, filename)
        return count

    async def get_memories_by_type(
        self,
        user_id: str,
        memory_type: MemoryType,
        limit: int = 10,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """Recupera memorias por tipo."""
        return await self.hybrid_search.search_by_type(
            memory_type=memory_type.value,
            limit=limit,
            chat_id=user_id,
            namespace=namespace,
        )

    async def delete_memories_by_query(
        self, user_id: str, query: str, namespace: str = "user"
    ) -> int:
        """Borrado suave por consulta."""
        results = await self.retrieve_context(
            user_id=user_id, query=query, limit=20, namespace=namespace
        )
        if not results:
            return 0
        ids = [r["id"] for r in results]
        count = await self.store.soft_delete_memories(ids)
        logger.info("Forgotten %d frags for %s", count, user_id)
        return count
