# src/agents/orchestrator/factory.py
"""
OrchestratorFactory for dependency injection and configuration.

Responsabilidad única: construcción y configuración del MasterOrchestrator
con todas sus dependencies inyectadas correctamente.
"""

import logging
import threading
from typing import Any

from src.core.registry import specialist_registry

from .graph_builder import OrchestratorGraphBuilder
from .master_orchestrator import MasterOrchestrator
from .routing.chaining_router import ConfigurableChainRouter
from .routing.enhanced_router import EnhancedFunctionCallingRouter
from .routing.event_router import EventRouter
from .specialist_cache import OptimizedSpecialistCache

logger = logging.getLogger(__name__)


class OrchestratorFactory:
    """
    Factory para construcción del MasterOrchestrator refactorizado.

    Responsabilidades:
    - Dependency injection de todas las strategies
    - Configuración de chaining rules
    - Inicialización ordenada de componentes
    - Provisión de configuración por defecto
    """

    @staticmethod
    def create_orchestrator(
        chaining_config: dict[str, Any] | None = None,
    ) -> MasterOrchestrator:
        """
        Crea MasterOrchestrator completamente configurado.

        Args:
            chaining_config: Configuración opcional de reglas de chaining

        Returns:
            MasterOrchestrator configurado y listo para usar
        """
        logger.info("Creando MasterOrchestrator refactorizado...")

        # 1. Crear y configurar cache de especialistas
        specialist_cache = OptimizedSpecialistCache()
        specialist_cache.initialize_cache(specialist_registry)

        # 2. Crear graph builder
        graph_builder = OrchestratorGraphBuilder(specialist_registry)

        # 3. Crear routing strategies
        routing_strategies = OrchestratorFactory._create_routing_strategies(
            specialist_cache, chaining_config
        )

        # 4. Crear orchestrator con dependencies inyectadas
        orchestrator = MasterOrchestrator(
            graph_builder=graph_builder,
            routing_strategies=routing_strategies,
            specialist_cache=specialist_cache,
        )

        logger.info("MasterOrchestrator refactorizado creado exitosamente")

        # Log configuración para debugging
        cache_stats = orchestrator.get_cache_stats()
        available_strategies = orchestrator.get_available_strategies()
        logger.info(f"Cache stats: {cache_stats}")
        logger.info(f"Strategies disponibles: {available_strategies}")

        return orchestrator

    @staticmethod
    def _create_routing_strategies(
        specialist_cache: OptimizedSpecialistCache,
        chaining_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Crea todas las routing strategies necesarias.

        Args:
            specialist_cache: Cache inicializado de especialistas
            chaining_config: Configuración de chaining rules

        Returns:
            Dict con routing strategies configuradas
        """
        # Configuración por defecto de chaining (Phase 3B compatibility)
        if chaining_config is None:
            chaining_config = OrchestratorFactory._get_default_chaining_config()

        strategies = {
            "function_calling": EnhancedFunctionCallingRouter(specialist_cache),
            "event_router": EventRouter(specialist_registry),
            "chaining": ConfigurableChainRouter(chaining_config),
        }

        logger.info(f"Routing strategies creadas: {list(strategies.keys())}")
        logger.info(f"Chaining config cargada: {chaining_config}")
        return strategies

    @staticmethod
    def _get_default_chaining_config() -> dict[str, Any]:
        """
        Retorna configuración por defecto para el sistema conversacional.

        Returns:
            Dict con configuración de chaining rules
        """
        return {
            "chain_rules": {
                "transcription_agent": {
                    "next_specialist": "chat_specialist",
                    "conditions": {"required_payload": {}},
                },
                "cbt_specialist": {
                    "next_specialist": "chat_specialist",
                    "conditions": {"required_payload": {}},
                },
                "chat_specialist": {"next_specialist": "__end__", "conditions": {}},
            },
            "fallback_action": "__end__",
        }


class LazyMasterOrchestrator:
    """
    Lazy initialization wrapper para MasterOrchestrator con thread-safety.

    Resuelve el problema de eager initialization durante import time
    usando el patrón Singleton con double-check locking.
    """

    _instance: MasterOrchestrator | None = None
    _lock = threading.Lock()

    def _get_instance(self) -> MasterOrchestrator:
        """Get or create the MasterOrchestrator instance."""
        if self._instance is None:
            with self._lock:
                if self._instance is None:  # Double-check locking
                    try:
                        self._instance = OrchestratorFactory.create_orchestrator()
                        logger.info("MasterOrchestrator inicializado lazily")
                    except Exception as e:
                        logger.error(f"Error en lazy initialization: {e}")
                        raise
        # El double-check asegura que para este punto _instance no es None
        return self._instance

    def __getattr__(self, name: str) -> Any:
        """Proxy all method calls to the actual instance."""
        instance = self._get_instance()
        return getattr(instance, name)

    async def run(self, initial_state: Any) -> Any:
        """Explicitly proxy the run method for better error handling."""
        instance = self._get_instance()
        return await instance.run(initial_state)

    def get_cache_stats(self) -> dict[str, Any]:
        """Explicitly proxy the cache stats method."""
        instance = self._get_instance()
        return instance.get_cache_stats()

    def get_available_strategies(self) -> list[str]:
        """Explicitly proxy the strategies method."""
        instance = self._get_instance()
        return instance.get_available_strategies()


# Thread-safe lazy instance
master_orchestrator = LazyMasterOrchestrator()
