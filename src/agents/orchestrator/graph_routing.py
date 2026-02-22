import logging
from typing import cast

from src.core.schemas import GraphStateV2

from .strategies import RoutingStrategy, SpecialistCache

logger = logging.getLogger(__name__)


class GraphRoutingHandler:
    """
    Maneja la lógica de enrutamiento dentro del grafo del orquestador.
    """

    def __init__(
        self,
        routing_strategies: dict[str, RoutingStrategy],
        specialist_cache: SpecialistCache,
    ) -> None:
        self._routing_strategies = routing_strategies
        self._cache = specialist_cache

    async def route_meta(self, state: GraphStateV2) -> GraphStateV2:
        """
        Meta routing delegado a FunctionCallingRouter o EventRouter.
        """
        session_id = state.get("session_id", "unknown-session")
        logger.info(f"[{session_id}] Iniciando meta-routing...")
        event = state["event"]

        # 1. Procesar perfilamiento proactivo (Detección de ubicación)
        if event.event_type == "text" and event.content:
            from src.core.profiling_manager import profiling_manager

            await profiling_manager.process_potential_location_data(
                str(event.chat_id), str(event.content)
            )

        # 2. Seleccionar strategy apropiada basada en event_type
        if event.event_type == "text":
            if "function_calling" in self._routing_strategies:
                await self._routing_strategies["function_calling"].route(state)
            else:
                logger.warning(
                    f"[{session_id}] FunctionCallingRouter no disponible "
                    "para evento de texto."
                )
        else:
            if "event_router" in self._routing_strategies:
                await self._routing_strategies["event_router"].route(state)
            else:
                logger.warning(
                    f"[{session_id}] EventRouter no disponible para evento "
                    f"tipo '{event.event_type}'."
                )

        logger.info(
            f"[{session_id}] Meta-routing finalizado. Próximo nodo "
            f"tentativo: {state.get('payload', {}).get('next_node')}"
        )
        return state

    async def route_chain(self, state: GraphStateV2) -> GraphStateV2:
        """
        Chain routing delegado a ChainingRouter.
        """
        session_id = state.get("session_id", "unknown-session")
        logger.info(f"[{session_id}] Iniciando chain-routing...")
        if "chaining" in self._routing_strategies:
            next_specialist = await self._routing_strategies["chaining"].route(state)
            state["payload"]["next_specialist"] = next_specialist
            logger.info(
                f"[{session_id}] Chain routing result: next_specialist = "
                f"{next_specialist}"
            )
        else:
            logger.warning(f"[{session_id}] ChainingRouter no disponible.")

        return state

    def initial_router_function(self, state: GraphStateV2) -> str:
        """
        Función de routing inicial para conditional edges.
        """
        session_id = state.get("session_id", "unknown-session")
        if state.get("error_message"):
            logger.error(
                f"[{session_id}] Error de enrutamiento detectado: "
                f"{state['error_message']}"
            )
            return "life_reflection"

        next_node = state.get("payload", {}).get("next_node")
        if not next_node:
            logger.warning(
                f"[{session_id}] No se pudo determinar el siguiente nodo desde "
                "el payload. Dirigiendo a reflexión."
            )
            return "life_reflection"

        # Validar que el nodo existe en specialists registrados
        all_specialists = self._cache.get_routable_specialists()
        valid_nodes = {s.name for s in all_specialists}
        valid_nodes.add("chat_specialist")  # Always valid

        if next_node not in valid_nodes:
            logger.warning(
                f"[{session_id}] Nodo '{next_node}' no es un especialista "
                f"válido. Nodos válidos: {valid_nodes}. Dirigiendo a reflexión."
            )
            return "life_reflection"

        logger.info(
            f"[{session_id}] Decisión de enrutamiento inicial: dirigir a '{next_node}'"
        )
        return cast(str, next_node)

    def chain_router_function(self, state: GraphStateV2) -> str:
        """
        Función de routing para chaining conditional edges.
        """
        session_id = state.get("session_id", "unknown-session")
        decision = "life_reflection"
        if "chaining" in self._routing_strategies:
            payload = state.get("payload", {})
            next_action = payload.get("next_action")

            if next_action == "respond_to_user":
                decision = "life_reflection"
            else:
                next_specialist = payload.get("next_specialist")
                if next_specialist:
                    decision = next_specialist

        logger.info(
            f"[{session_id}] Decisión de enrutamiento en cadena: dirigir a '{decision}'"
        )
        return decision
