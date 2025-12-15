# src/agents/orchestrator/strategies.py
"""
Interfaces core para Strategy Pattern del orchestrator.

Define contratos para routing strategies y graph building siguiendo
principios de dependency inversion y clean architecture.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.core.registry import SpecialistRegistry
from src.core.schemas import GraphStateV2


class RoutingStrategy(ABC):
    """
    Interface para estrategias de enrutamiento.

    Implementa Strategy Pattern para diferentes tipos de routing:
    - Function Calling con LLM
    - Event-based routing
    - Chaining entre especialistas
    """

    @abstractmethod
    async def route(self, state: GraphStateV2) -> str:
        """
        Determina el siguiente nodo basado en el estado actual.

        Args:
            state: Estado actual del grafo con event, payload, etc.

        Returns:
            str: Nombre del siguiente nodo o "__end__" para finalizar
        """
        pass


class GraphBuilder(ABC):
    """
    Interface para construcción del grafo de orquestación.

    Separa la responsabilidad de construir el grafo LangGraph
    de la lógica de enrutamiento.
    """

    @abstractmethod
    def build(self, routing_functions: dict[str, Any]) -> Any:
        """
        Construye y retorna el grafo de orquestación.

        Args:
            routing_functions: Funciones de routing para inyectar al grafo

        Returns:
            Compiled LangGraph StateGraph
        """
        pass


class SpecialistCache(ABC):
    """
    Interface para cache management de especialistas.

    Separa la responsabilidad de optimización y caching
    del routing core logic.
    """

    @abstractmethod
    def initialize_cache(self, specialist_registry: SpecialistRegistry) -> None:
        """Inicializa cache de especialistas y herramientas."""
        pass

    @abstractmethod
    def get_routable_specialists(self) -> list[Any]:
        """Retorna lista de especialistas enrutables (cached)."""
        pass

    @abstractmethod
    def get_routable_tools(self) -> list[Any]:
        """Retorna lista de herramientas enrutables (cached)."""
        pass

    @abstractmethod
    def get_tool_to_specialist_map(self) -> dict[str, str]:
        """Retorna mapeo tool_name -> specialist_name (O(1) lookup)."""
        pass

    @abstractmethod
    def get_llm_with_tools(self) -> Any:
        """Retorna LLM pre-configurado con tools para Function Calling."""
        pass

    @abstractmethod
    def has_routable_tools(self) -> bool:
        """Verifica si hay herramientas enrutables disponibles."""
        pass

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """Retorna estadísticas del cache para debugging/monitoring."""
        pass
