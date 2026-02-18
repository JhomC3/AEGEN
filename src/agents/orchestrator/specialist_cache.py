# src/agents/orchestrator/specialist_cache.py
"""
SpecialistCache implementation.

Responsabilidad única: cache management y optimización de lookup de especialistas.
Extraído del MasterOrchestrator para cumplir SRP y facilitar testing.
"""

import logging
from typing import Any

from src.core.engine import llm
from src.core.registry import SpecialistRegistry

from .strategies import SpecialistCache

logger = logging.getLogger(__name__)

# Constante para especialista excluido del routing automático
CHAT_SPECIALIST_NODE = "chat_specialist"


class OptimizedSpecialistCache(SpecialistCache):
    """
    Cache optimizado para especialistas y herramientas.

    Responsabilidades:
    - Pre-cálculo de herramientas y mapeos para eficiencia O(1)
    - Binding de LLM con tools para Function Calling
    - Filtrado de especialistas enrutables
    - Mapeo directo tool_name → specialist_name

    Implementa optimizaciones recomendadas por Gemini para performance.
    """

    def __init__(self) -> None:
        """Initialize cache con estado limpio."""
        self._routable_specialists: list[Any] = []
        self._routable_tools: list[Any] = []
        self._tool_to_specialist_map: dict[str, str] = {}
        self._llm_with_tools: Any = None
        self._is_initialized = False

    def initialize_cache(self, specialist_registry: SpecialistRegistry) -> None:
        """
        Inicializa cache de especialistas y herramientas.

        Pre-calcula herramientas y mapeos para optimizar el enrutamiento.
        Siguiendo recomendaciones de Gemini para eficiencia.

        Args:
            specialist_registry: Registry de especialistas a cachear
        """
        logger.info("Inicializando cache de especialistas...")

        # Obtener todos los especialistas, incluyendo el de chat
        self._routable_specialists = specialist_registry.get_all_specialists()

        # Cache de herramientas
        self._routable_tools = [s.tool for s in self._routable_specialists]

        # Mapeo directo tool_name → specialist_name para O(1) lookup
        self._tool_to_specialist_map = {
            s.tool.name: s.name for s in self._routable_specialists
        }

        # LLM con herramientas pre-vinculadas para Function Calling
        if self._routable_tools:
            self._llm_with_tools = llm.bind_tools(self._routable_tools)
            logger.info(
                f"LLM vinculado con {len(self._routable_tools)} herramientas de especialistas"
            )
        else:
            self._llm_with_tools = llm
            logger.warning(
                "No hay especialistas enrutables, usando LLM sin herramientas"
            )

        self._is_initialized = True
        logger.info(
            f"Cache inicializado: {len(self._routable_specialists)} especialistas, "
            f"{len(self._routable_tools)} herramientas"
        )

    def get_routable_specialists(self) -> list[Any]:
        """
        Retorna lista de especialistas enrutables (cached).

        Returns:
            Lista de especialistas que pueden ser enrutados automáticamente

        Raises:
            RuntimeError: Si el cache no ha sido inicializado
        """
        self._ensure_initialized()
        return self._routable_specialists.copy()

    def get_routable_tools(self) -> list[Any]:
        """
        Retorna lista de herramientas enrutables (cached).

        Returns:
            Lista de tools de especialistas para Function Calling
        """
        self._ensure_initialized()
        return self._routable_tools.copy()

    def get_tool_to_specialist_map(self) -> dict[str, str]:
        """
        Retorna mapeo tool_name -> specialist_name (O(1) lookup).

        Returns:
            Dict para lookup directo de especialista por nombre de tool
        """
        self._ensure_initialized()
        return self._tool_to_specialist_map.copy()

    def get_llm_with_tools(self) -> Any:
        """
        Retorna LLM pre-configurado con tools para Function Calling.

        Returns:
            LLM instance con tools binding o LLM básico si no hay tools
        """
        self._ensure_initialized()
        return self._llm_with_tools

    def has_routable_tools(self) -> bool:
        """
        Verifica si hay herramientas enrutables disponibles.

        Returns:
            True si hay al menos una herramienta enrutable, False otherwise
        """
        self._ensure_initialized()
        return len(self._routable_tools) > 0

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Retorna estadísticas del cache para debugging/monitoring.

        Returns:
            Dict con estadísticas del cache
        """
        if not self._is_initialized:
            return {"initialized": False}

        return {
            "initialized": True,
            "routable_specialists_count": len(self._routable_specialists),
            "routable_tools_count": len(self._routable_tools),
            "tool_mappings_count": len(self._tool_to_specialist_map),
            "has_llm_with_tools": self._llm_with_tools is not None,
            "specialist_names": [s.name for s in self._routable_specialists],
            "tool_names": list(self._tool_to_specialist_map.keys()),
        }

    def _ensure_initialized(self) -> None:
        """
        Verifica que el cache haya sido inicializado.

        Raises:
            RuntimeError: Si initialize_cache() no ha sido llamado
        """
        if not self._is_initialized:
            raise RuntimeError(
                "Cache no inicializado. Llamar initialize_cache() primero."
            )
