# src/memory/hybrid_coordinator.py
"""
Coordinador principal para memoria híbrida Redis + ChromaDB.

Responsabilidad única: coordinar estrategias de almacenamiento
entre Redis (cache rápido) y ChromaDB (persistencia vectorial).
"""

import logging
from enum import Enum
from typing import Any

from src.memory.consistency_manager import ConsistencyManager
from src.memory.redis_fallback import RedisFallbackManager
from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class StorageStrategy(str, Enum):
    """Estrategias de almacenamiento híbrido."""

    REDIS_FIRST = "redis_first"  # Redis primario, ChromaDB backup
    CHROMA_FIRST = "chroma_first"  # ChromaDB primario, Redis cache
    BOTH_SYNC = "both_sync"  # Sincronización en ambos
    AUTO_DECIDE = "auto_decide"  # Decisión automática por contexto


class HybridMemoryCoordinator:
    """Coordinador principal para memoria híbrida Redis + ChromaDB."""

    def __init__(
        self,
        vector_manager: VectorMemoryManager,
        redis_manager: RedisFallbackManager,
        consistency_manager: ConsistencyManager,
    ):
        self.vector_manager = vector_manager
        self.redis_manager = redis_manager
        self.consistency_manager = consistency_manager
        self.logger = logging.getLogger(__name__)

    async def store_context_hybrid(
        self,
        user_id: str,
        content: str,
        context_type: MemoryType,
        strategy: StorageStrategy = StorageStrategy.AUTO_DECIDE,
        ttl: int = 3600,
    ) -> bool:
        """Almacena contexto usando estrategia híbrida."""
        try:
            # Decidir estrategia automáticamente si es necesario
            if strategy == StorageStrategy.AUTO_DECIDE:
                strategy = self._decide_storage_strategy(content, context_type)

            success = False

            if strategy == StorageStrategy.REDIS_FIRST:
                success = await self._store_redis_first(
                    user_id, content, context_type, ttl
                )
            elif strategy == StorageStrategy.CHROMA_FIRST:
                success = await self._store_chroma_first(user_id, content, context_type)
            elif strategy == StorageStrategy.BOTH_SYNC:
                success = await self._store_both_sync(
                    user_id, content, context_type, ttl
                )

            self.logger.debug(
                f"Hybrid storage {strategy} for user {user_id}: {success}"
            )
            return success

        except Exception as e:
            self.logger.error(
                f"Failed hybrid storage for user {user_id}: {e}", exc_info=True
            )
            return False

    async def retrieve_context_hybrid(
        self,
        user_id: str,
        query: str,
        strategy: StorageStrategy = StorageStrategy.REDIS_FIRST,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Recupera contexto usando estrategia híbrida."""
        try:
            if strategy == StorageStrategy.REDIS_FIRST:
                results = await self.redis_manager.get_from_redis_or_fallback(
                    user_id, query
                )
                if results:
                    return results[:limit]
                # Fallback a ChromaDB
                return await self._query_chroma_fallback(
                    user_id, query, MemoryType.CONVERSATION, limit
                )

            elif strategy == StorageStrategy.CHROMA_FIRST:
                results = await self._query_chroma_fallback(
                    user_id, query, MemoryType.CONVERSATION, limit
                )
                if results:
                    # Cache results en Redis para siguiente vez
                    await self._cache_results_to_redis(user_id, query, results)
                return results

            return []

        except Exception as e:
            self.logger.error(
                f"Failed hybrid retrieval for user {user_id}: {e}", exc_info=True
            )
            return []

    async def sync_redis_to_chroma(self, user_id: str) -> bool:
        """Sincroniza datos de Redis a ChromaDB para persistencia."""
        try:
            # Obtener datos de Redis que necesitan persistencia
            redis_data = await self.redis_manager.get_persistent_data(user_id)

            if not redis_data:
                return True

            # Almacenar en ChromaDB
            for data_item in redis_data:
                await self.vector_manager.store_context(
                    user_id=user_id,
                    content=data_item["content"],
                    context_type=MemoryType(data_item.get("type", "conversation")),
                    metadata=data_item.get("metadata", {}),
                )

            self.logger.info(
                f"Synced {len(redis_data)} items from Redis to ChromaDB for user {user_id}"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed Redis to ChromaDB sync for user {user_id}: {e}", exc_info=True
            )
            return False

    async def cleanup_expired_redis_entries(self) -> int:
        """Limpia entradas expiradas de Redis."""
        try:
            cleaned_count = await self.redis_manager.cleanup_expired_entries()
            if cleaned_count > 0:
                self.logger.info(f"Cleaned {cleaned_count} expired Redis entries")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed Redis cleanup: {e}", exc_info=True)
            return 0

    def _decide_storage_strategy(
        self, content: str, context_type: MemoryType
    ) -> StorageStrategy:
        """Decide estrategia basada en contenido y tipo."""
        # Estrategia simple: conversaciones recientes a Redis, documentos a ChromaDB
        if context_type == MemoryType.CONVERSATION and len(content) < 1000:
            return StorageStrategy.REDIS_FIRST
        elif context_type in [MemoryType.DOCUMENT, MemoryType.PREFERENCE]:
            return StorageStrategy.CHROMA_FIRST
        else:
            return StorageStrategy.BOTH_SYNC

    async def _store_redis_first(
        self, user_id: str, content: str, context_type: MemoryType, ttl: int
    ) -> bool:
        """Estrategia Redis primero."""
        redis_success = await self.redis_manager.cache_context(user_id, content, ttl)
        if redis_success:
            # Almacenar también en ChromaDB para persistencia
            await self.vector_manager.store_context(
                user_id, content, context_type, metadata={}
            )
        return redis_success

    async def _store_chroma_first(
        self, user_id: str, content: str, context_type: MemoryType
    ) -> bool:
        """Estrategia ChromaDB primero."""
        return await self.vector_manager.store_context(
            user_id, content, context_type, metadata={}
        )

    async def _store_both_sync(
        self, user_id: str, content: str, context_type: MemoryType, ttl: int
    ) -> bool:
        """Estrategia sincronizada en ambos."""
        chroma_success = await self.vector_manager.store_context(
            user_id, content, context_type, metadata={}
        )
        redis_success = await self.redis_manager.cache_context(user_id, content, ttl)
        return chroma_success and redis_success

    async def _query_chroma_fallback(
        self, user_id: str, query: str, context_type: MemoryType, limit: int
    ) -> list[dict[str, Any]]:
        """Consulta ChromaDB como fallback."""
        return await self.vector_manager.retrieve_context(
            user_id, query, context_type, limit=limit
        )

    async def _cache_results_to_redis(
        self, user_id: str, query: str, results: list[dict[str, Any]]
    ) -> None:
        """Cache resultados en Redis."""
        cache_key = f"query_cache_{query[:50]}"
        await self.redis_manager.cache_to_redis(
            user_id, cache_key, {"results": results}, ttl=300
        )
