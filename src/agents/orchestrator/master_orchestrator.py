# src/agents/orchestrator/master_orchestrator.py
"""
Refactored MasterOrchestrator as minimal coordinator.

Responsabilidad única: coordinación de routing strategies y graph execution.
Todas las responsabilidades complejas delegadas a strategies inyectadas.
"""

import logging
from typing import Any, cast

from src.core.schemas import GraphStateV2

from .strategies import GraphBuilder, RoutingStrategy, SpecialistCache

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Coordinador minimalista del sistema de orquestación.

    Responsabilidades (después de refactorización):
    - Coordinación de routing strategies
    - Ejecución del grafo construido
    - Delegation de decisiones a strategies inyectadas

    Ya NO es responsable de:
    - Construcción del grafo (delegado a GraphBuilder)
    - Lógica de routing (delegado a RoutingStrategy implementations)
    - Cache management (delegado a SpecialistCache)
    - Function calling logic (delegado a FunctionCallingRouter)
    - Chaining logic (delegado a ChainingRouter)
    """

    def __init__(
        self,
        graph_builder: GraphBuilder,
        routing_strategies: dict[str, RoutingStrategy],
        specialist_cache: SpecialistCache,
    ):
        """
        Initialize orchestrator con dependencies inyectadas.

        Args:
            graph_builder: Strategy para construcción del grafo
            routing_strategies: Mapping de routing strategies por nodo
            specialist_cache: Cache de especialistas y herramientas
        """
        self._graph_builder = graph_builder
        self._routing_strategies = routing_strategies
        self._cache = specialist_cache

        # Construir grafo con routing functions delegadas
        self.graph = self._build_orchestration_graph()

        logger.info("MasterOrchestrator inicializado con dependencies inyectadas")

    def _build_orchestration_graph(self) -> Any:
        """
        Construye el grafo delegando a GraphBuilder.

        Returns:
            Compiled LangGraph StateGraph
        """
        routing_functions = {
            "meta_router_fn": self._route_meta,
            "chain_router_fn": self._route_chain,
            "initial_router_fn": self._initial_router_function,
            "chain_router_decision_fn": self._chain_router_function,
        }

        return self._graph_builder.build(routing_functions)

    async def _route_meta(self, state: GraphStateV2) -> GraphStateV2:
        """
        Meta routing delegado a FunctionCallingRouter o EventRouter.

        Args:
            state: Estado del grafo

        Returns:
            Estado modificado por la strategy
        """
        session_id = state.get("session_id", "unknown-session")
        logger.info(f"[{session_id}] Iniciando meta-routing...")
        event = state["event"]

        # Seleccionar strategy apropiada basada en event_type
        if event.event_type == "text":
            if "function_calling" in self._routing_strategies:
                await self._routing_strategies["function_calling"].route(state)
            else:
                logger.warning(
                    f"[{session_id}] FunctionCallingRouter no disponible para evento de texto."
                )
        else:
            if "event_router" in self._routing_strategies:
                await self._routing_strategies["event_router"].route(state)
            else:
                logger.warning(
                    f"[{session_id}] EventRouter no disponible para evento tipo '{event.event_type}'."
                )

        logger.info(
            f"[{session_id}] Meta-routing finalizado. Próximo nodo tentativo: {state.get('payload', {}).get('next_node')}"
        )
        return state

    async def _route_chain(self, state: GraphStateV2) -> GraphStateV2:
        """
        Chain routing delegado a ChainingRouter.

        Args:
            state: Estado del grafo

        Returns:
            Estado modificado por la strategy
        """
        session_id = state.get("session_id", "unknown-session")
        logger.info(f"[{session_id}] Iniciando chain-routing...")
        if "chaining" in self._routing_strategies:
            next_specialist = await self._routing_strategies["chaining"].route(state)
            # CRITICAL FIX: Capturar y guardar el resultado del chaining
            state["payload"]["next_specialist"] = next_specialist
            logger.info(
                f"[{session_id}] Chain routing result: next_specialist = {next_specialist}"
            )
        else:
            logger.warning(f"[{session_id}] ChainingRouter no disponible.")

        return state

    def _initial_router_function(self, state: GraphStateV2) -> str:
        """
        Función de routing inicial para conditional edges.

        Args:
            state: Estado del grafo

        Returns:
            str: Nombre del siguiente nodo
        """
        session_id = state.get("session_id", "unknown-session")
        if state.get("error_message"):
            logger.error(
                f"[{session_id}] Error de enrutamiento detectado: {state['error_message']}"
            )
            return "__end__"

        next_node = state.get("payload", {}).get("next_node")
        if not next_node:
            logger.warning(
                f"[{session_id}] No se pudo determinar el siguiente nodo desde el payload. Finalizando."
            )
            return "__end__"

        # Validar que el nodo existe en specialists registrados
        all_specialists = self._cache.get_routable_specialists()
        valid_nodes = {s.name for s in all_specialists}
        valid_nodes.add("chat_specialist")  # Always valid

        if next_node not in valid_nodes:
            logger.warning(
                f"[{session_id}] Nodo '{next_node}' no es un especialista válido. Nodos válidos: {valid_nodes}. Finalizando."
            )
            return "__end__"

        logger.info(
            f"[{session_id}] Decisión de enrutamiento inicial: dirigir a '{next_node}'"
        )
        return cast(str, next_node)

    def _chain_router_function(self, state: GraphStateV2) -> str:
        """
        Función de routing para chaining conditional edges.

        Args:
            state: Estado del grafo

        Returns:
            str: Siguiente nodo en el chain o "__end__"
        """
        session_id = state.get("session_id", "unknown-session")
        decision = "__end__"
        if "chaining" in self._routing_strategies:
            payload = state.get("payload", {})
            next_action = payload.get("next_action")

            if next_action == "respond_to_user":
                decision = "__end__"
            else:
                next_specialist = payload.get("next_specialist")
                if next_specialist:
                    decision = next_specialist

        logger.info(
            f"[{session_id}] Decisión de enrutamiento en cadena: dirigir a '{decision}'"
        )
        return decision

    async def run(self, initial_state: GraphStateV2) -> dict:
        """
        Ejecuta el grafo del orquestador.

        Args:
            initial_state: Estado inicial del grafo

        Returns:
            dict: Estado final después de la ejecución
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
