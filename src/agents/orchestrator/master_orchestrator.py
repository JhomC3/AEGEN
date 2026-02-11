# src/agents/orchestrator/master_orchestrator.py
"""
Refactored MasterOrchestrator as minimal coordinator.

Responsabilidad única: coordinación de routing strategies y graph execution.
Todas las responsabilidades complejas delegadas a strategies inyectadas.
"""

import logging
from typing import Any, cast

from src.core.schemas import GraphStateV2

from .graph_routing import GraphRoutingHandler
from .strategies import GraphBuilder, RoutingStrategy, SpecialistCache

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Coordinador minimalista del sistema de orquestación.
    """

    def __init__(
        self,
        graph_builder: GraphBuilder,
        routing_strategies: dict[str, RoutingStrategy],
        specialist_cache: SpecialistCache,
    ):
        """
        Initialize orchestrator con dependencies inyectadas.
        """
        self._graph_builder = graph_builder
        self._routing_strategies = routing_strategies
        self._cache = specialist_cache
        self._graph_routing = GraphRoutingHandler(routing_strategies, specialist_cache)

        # Construir grafo con routing functions delegadas
        self.graph = self._build_orchestration_graph()

        logger.info("MasterOrchestrator inicializado con dependencies inyectadas")

    def _build_orchestration_graph(self) -> Any:
        """
        Construye el grafo delegando a GraphBuilder.
        """
        routing_functions = {
            "meta_router_fn": self._graph_routing.route_meta,
            "chain_router_fn": self._graph_routing.route_chain,
            "initial_router_fn": self._graph_routing.initial_router_function,
            "chain_router_decision_fn": self._graph_routing.chain_router_function,
        }

        return self._graph_builder.build(routing_functions)

    async def run(self, initial_state: GraphStateV2) -> dict:
        """
        Ejecuta el grafo del orquestador.
        """
        session_id = initial_state.get("session_id", "unknown-session")
        logger.info(
            f"[{session_id}] >>> Iniciando ejecución del grafo orquestador. Evento: {initial_state.get('event')}"
        )

        if not self.graph:
            logger.error(
                f"[{session_id}] Grafo no disponible. No se puede ejecutar la orquestación."
            )
            initial_state["error_message"] = "Orquestador no disponible"
            return dict(initial_state)

        try:
            final_state_dict = await self.graph.ainvoke(initial_state)
            logger.info(
                f"[{session_id}] <<< Finalizada ejecución del grafo orquestador."
            )
            return cast(dict, final_state_dict)
        except Exception as e:
            logger.error(
                f"[{session_id}] Error catastrófico ejecutando el grafo: {e}",
                exc_info=True,
            )
            initial_state["error_message"] = f"Error de ejecución: {e}"
            return dict(initial_state)

    def get_cache_stats(self) -> dict[str, Any]:
        """Retorna estadísticas del cache para monitoring."""
        return self._cache.get_cache_stats()

    def get_available_strategies(self) -> list:
        """Retorna lista de strategies disponibles."""
        return list(self._routing_strategies.keys())
