# src/memory/memory_factory.py
"""
Factory para componentes de memoria híbrida.

Responsabilidad única: crear e inyectar dependencias entre
componentes de memoria híbrida Redis + ChromaDB.
"""

import logging
from typing import Optional

from src.memory.redis_fallback import RedisFallbackManager
from src.memory.consistency_manager import ConsistencyManager, ConsistencyLevel
from src.memory.hybrid_coordinator import HybridMemoryCoordinator
from src.core.vector_memory_manager import VectorMemoryManager

logger = logging.getLogger(__name__)


class MemoryFactory:
    """Factory para componentes de memoria híbrida."""

    def __init__(self, vector_manager: VectorMemoryManager, redis_client=None):
        self.vector_manager = vector_manager
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Cache de componentes
        self._redis_manager: Optional[RedisFallbackManager] = None
        self._consistency_manager: Optional[ConsistencyManager] = None
        self._hybrid_coordinator: Optional[HybridMemoryCoordinator] = None

    def get_redis_manager(self) -> RedisFallbackManager:
        """Crea o retorna RedisFallbackManager."""
        if self._redis_manager is None:
            self._redis_manager = RedisFallbackManager(self.redis_client)
            self.logger.debug("Created RedisFallbackManager instance")
        return self._redis_manager

    def get_consistency_manager(self, consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL) -> ConsistencyManager:
        """Crea o retorna ConsistencyManager."""
        if self._consistency_manager is None:
            self._consistency_manager = ConsistencyManager(consistency_level)
            self.logger.debug(f"Created ConsistencyManager with level: {consistency_level}")
        return self._consistency_manager

    def get_hybrid_coordinator(self) -> HybridMemoryCoordinator:
        """Crea o retorna HybridMemoryCoordinator con todas las dependencias."""
        if self._hybrid_coordinator is None:
            redis_manager = self.get_redis_manager()
            consistency_manager = self.get_consistency_manager()
            
            self._hybrid_coordinator = HybridMemoryCoordinator(
                self.vector_manager,
                redis_manager,
                consistency_manager
            )
            self.logger.debug("Created HybridMemoryCoordinator instance")
            
        return self._hybrid_coordinator

    def create_memory_components(self) -> dict:
        """Crea todos los componentes de memoria híbrida."""
        return {
            'redis_manager': self.get_redis_manager(),
            'consistency_manager': self.get_consistency_manager(),
            'hybrid_coordinator': self.get_hybrid_coordinator()
        }