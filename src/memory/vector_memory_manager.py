# src/memory/vector_memory_manager.py
"""
Public API for managing and retrieving memories.

Integrates IngestionPipeline and HybridSearch for high-level operations.
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
        Inicializa el manager con una base de datos SQLite.
        """
        # Usar store proporcionado o crear uno nuevo con la configuración global
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
        """
        Recupera memorias relevantes para una consulta usando búsqueda híbrida.

        Args:
            user_id: ID del usuario (chat_id)
            query: Consulta en texto
            context_type: Opcional, filtrar por tipo de memoria
            limit: Número máximo de resultados
            namespace: Espacio de nombres (default 'user')

        Returns:
            Lista de fragmentos de memoria relevantes.
        """
        results = await self.hybrid_search.search(
            query=query, limit=limit, chat_id=user_id, namespace=namespace
        )

        # Transparencia RAG
        if results:
            sources: dict[str, int] = {}
            for r in results:
                meta = r.get("metadata", {})
                source = meta.get("source", r.get("memory_type", "unknown"))
                sources[source] = sources.get(source, 0) + 1
            source_summary = ", ".join(f"{k}: {v}" for k, v in sources.items())
            logger.info(
                f"[RAG] Retrieved {len(results)} fragments for user={user_id}, "
                f"namespace={namespace} | Sources: {source_summary}"
            )
        else:
            logger.debug(
                f"[RAG] No fragments found for user={user_id}, query='{query[:50]}...'"
            )

        # Si se especificó un tipo de contexto, podríamos filtrar aquí
        # aunque es mejor hacerlo en la query SQL si fuera crítico
        if context_type:
            results = [r for r in results if r["memory_type"] == context_type.value]

        return results

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
        Soft-deletes memories matching a search query. Used by /olvidar command.
        Returns the number of memories deactivated.
        """
        results = await self.retrieve_context(
            user_id=user_id, query=query, limit=20, namespace=namespace
        )
        if not results:
            return 0

        memory_ids = [r["id"] for r in results]
        count = await self.store.soft_delete_memories(memory_ids)
        logger.info(
            f"[PRIVACY] Soft-deleted {count} memories for user={user_id}, query='{query[:50]}'"
        )
        return count
