# src/memory/vector_memory_manager.py
"""
API pública para la gestión y recuperación de memorias.

Integra IngestionPipeline e HybridSearch para operaciones de alto nivel.
"""

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
    """
    Gestor de memoria vectorial y de texto de alto nivel.
    """

    def __init__(self, store: SQLiteStore | None = None):
        """
        Inicializa el gestor con una base de datos SQLite.
        """
        # Usar store proporcionado o crear uno nuevo con la configuración global
        self.store = store or SQLiteStore(settings.SQLITE_DB_PATH)
        self.pipeline = IngestionPipeline(self.store)
        self.hybrid_search = HybridSearch(self.store)
        logger.info("VectorMemoryManager inicializado")

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        context_type: MemoryType | None = None,
        limit: int = 5,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """
        Recupera memorias relevantes usando búsqueda híbrida.
        Genera trazas RAG estructuradas para observabilidad.
        """
        import time

        start_time = time.monotonic()

        results = await self.hybrid_search.search(
            query=query, limit=limit, chat_id=user_id, namespace=namespace
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Traza RAG estructurada (ADR-0025)
        self._log_rag_trace(
            user_id=user_id,
            namespace=namespace,
            query=query,
            results=results,
            elapsed_ms=elapsed_ms,
        )

        # Si se especificó un tipo de contexto, podríamos filtrar aquí
        if context_type:
            results = [r for r in results if r["memory_type"] == context_type.value]

        return results

    def _log_rag_trace(
        self,
        user_id: str,
        namespace: str,
        query: str,
        results: list[dict[str, Any]],
        elapsed_ms: float,
    ) -> None:
        """Emite una traza RAG estructurada como log JSON."""
        fragments = [
            {
                "id": r["id"],
                "score": round(r.get("score", 0), 4),
                "source": r.get("metadata", {}).get("filename", "unknown"),
                "type": r.get("memory_type", "unknown"),
                "preview": r["content"][:120],
            }
            for r in results
        ]

        logger.info(
            f"[RAG-TRACE] {namespace}: {len(results)} fragments, "
            f"{elapsed_ms:.0f}ms | query='{query[:50]}...'",
            extra={
                "event": "rag_retrieval",
                "user_id": user_id,
                "namespace": namespace,
                "query_preview": query[:80],
                "results_count": len(results),
                "latency_ms": round(elapsed_ms, 1),
                "fragments": fragments,
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
        """
        Almacena un contenido en el sistema de memoria de largo plazo.

        Args:
            user_id: ID del usuario (chat_id)
            content: Texto a almacenar
            context_type: Tipo de memoria
            metadata: Metadatos adicionales
            namespace: Espacio de nombres

        Returns:
            Número de nuevos fragmentos almacenados.
        """
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
        """
        Elimina (borrado suave) todo el conocimiento asociado a un archivo específico.
        """
        count = await self.store.delete_memories_by_filename(filename, namespace)
        if count > 0:
            logger.info(
                f"[KNOWLEDGE] Borrado suave de {count} fragmentos del archivo '{filename}' "
                f"en namespace '{namespace}'"
            )
        return count

    async def get_memories_by_type(
        self,
        user_id: str,
        memory_type: MemoryType,
        limit: int = 10,
        namespace: str = "user",
    ) -> list[dict[str, Any]]:
        """
        Recupera las memorias más recientes de un tipo específico.
        """
        return await self.hybrid_search.search_by_type(
            memory_type=memory_type.value,
            limit=limit,
            chat_id=user_id,
            namespace=namespace,
        )

    async def delete_memories_by_query(
        self,
        user_id: str,
        query: str,
        namespace: str = "user",
    ) -> int:
        """
        Realiza un borrado suave (soft-delete) de memorias que coinciden con una consulta.
        Utilizado por el comando /olvidar. Retorna el número de memorias desactivadas.
        """
        results = await self.retrieve_context(
            user_id=user_id, query=query, limit=20, namespace=namespace
        )
        if not results:
            return 0

        memory_ids = [r["id"] for r in results]
        count = await self.store.soft_delete_memories(memory_ids)
        logger.info(
            f"[PRIVACIDAD] Borrado suave de {count} memorias para usuario={user_id}, consulta='{query[:50]}'"
        )
        return count
