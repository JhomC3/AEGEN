# src/agents/orchestrator.py
import logging
from typing import Any, cast

from langgraph.graph import StateGraph

from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    El orquestador central (MasterRouter) que dirige el flujo de trabajo
    de forma dinámica basándose en las capacidades de los especialistas registrados.
    Implementa un enrutamiento basado en el tipo de evento.
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """
        Construye dinámicamente el grafo de enrutamiento principal con chaining
        basándose en los especialistas registrados.

        Chain Architecture:
        meta_router → specialist → chain_router → next_specialist → ... → END
        """
        graph_builder = StateGraph(GraphStateV2)

        # 1. Nodo de entrada: Meta-enrutador basado en capacidades.
        graph_builder.add_node("meta_router", self._meta_route_request)

        # 2. Nodos de especialistas: un nodo por cada especialista.
        all_specialists = specialist_registry.get_all_specialists()
        for specialist in all_specialists:
            compiled_graph = cast(Any, specialist.graph)
            graph_builder.add_node(specialist.name, compiled_graph.ainvoke)

            # NUEVA ARQUITECTURA: Especialistas van a chain_router, no a END
            graph_builder.add_edge(specialist.name, "chain_router")

        # 3. Nuevo nodo: Chain router para determinar siguiente especialista
        graph_builder.add_node("chain_router", self._chain_route_request)

        # 4. Lógica de enrutamiento condicional desde el meta-enrutador.
        graph_builder.set_entry_point("meta_router")

        def initial_router_function(state: GraphStateV2) -> str:
            """Función de enrutamiento inicial desde meta_router."""
            decision = self._decide_next_node(state)
            # El valor de retorno debe ser uno de los nodos registrados o END
            if decision not in {s.name for s in all_specialists}:
                return "__end__"
            return decision

        def chain_router_function(state: GraphStateV2) -> str:
            """Función de enrutamiento para chaining entre especialistas."""
            return self._decide_chain_next_node(state, all_specialists)

        graph_builder.add_conditional_edges(
            "meta_router",
            initial_router_function,
        )

        graph_builder.add_conditional_edges(
            "chain_router",
            chain_router_function,
        )

        return graph_builder.compile()

    async def _meta_route_request(self, state: GraphStateV2) -> GraphStateV2:
        """
        Primera capa de enrutamiento. Determina el especialista o grupo de especialistas
        basándose en el `event_type` del evento canónico.
        """
        event = state["event"]
        event_type = event.event_type
        logger.info(f"Meta-enrutador: procesando evento de tipo '{event_type}'.")

        # Encontrar especialistas que puedan manejar este tipo de evento.
        capable_specialists = [
            s
            for s in specialist_registry.get_all_specialists()
            if event_type in cast(SpecialistInterface, s).get_capabilities()
        ]

        if not capable_specialists:
            logger.warning(
                f"No se encontraron especialistas para el tipo de evento '{event_type}'."
            )
            state["error_message"] = (
                f"No hay especialistas para manejar '{event_type}'."
            )
            return state

        if len(capable_specialists) == 1:
            # Si solo hay un especialista, la decisión es directa.
            specialist = capable_specialists[0]
            logger.info(
                f"Enrutamiento directo al único especialista capaz: '{specialist.name}'."
            )
            state["payload"]["next_node"] = specialist.name
            return state
        else:
            # Si hay múltiples especialistas, usar un LLM para desambiguar.
            logger.info(
                f"Múltiples especialistas encontrados para '{event_type}'. Usando LLM para desambiguar."
            )
            # Esta lógica se puede expandir como se describió en el plan.
            # Por ahora, para mantenerlo simple, tomaremos el primero.
            # TODO: Implementar desambiguación por LLM cuando sea necesario.
            specialist = capable_specialists[0]
            logger.info(
                f"Tomando el primer especialista por defecto: '{specialist.name}'."
            )
            state["payload"]["next_node"] = specialist.name
            return state

    def _decide_next_node(self, state: GraphStateV2) -> str:
        """
        Lee la decisión del meta-enrutador y devuelve el nombre del siguiente nodo.
        """
        if state.get("error_message"):
            logger.error(
                f"Error de enrutamiento, finalizando: {state['error_message']}"
            )
            return "__end__"

        next_node = state.get("payload", {}).get("next_node")
        if not next_node:
            logger.warning("No se pudo determinar el siguiente nodo. Finalizando.")
            return "__end__"

        logger.info(f"Decisión de enrutamiento: dirigir a '{next_node}'.")
        return cast(str, next_node)

    async def _chain_route_request(self, state: GraphStateV2) -> GraphStateV2:
        """
        Segundo nivel de enrutamiento: determina si hay que encadenar a otro especialista
        o si es el momento de finalizar.

        Lógica de chaining Phase 3B:
        1. Si viene de transcription_agent → chain a planner_agent
        2. Si viene de planner_agent → END (responder al usuario)
        3. Si hay error → END
        """
        current_payload = state.get("payload", {})
        last_specialist = current_payload.get("last_specialist")
        next_action = current_payload.get("next_action")

        logger.info(
            f"Chain router: analizando estado desde {last_specialist}, next_action: {next_action}"
        )

        # Marcar el especialista actual como completado
        if not last_specialist:
            # Inferir del flujo actual: si hay transcripción → viene de transcription_agent
            event = state.get("event")
            if event and hasattr(event, "event_type") and event.event_type == "audio":
                last_specialist = "transcription_agent"
            else:
                last_specialist = "unknown"

        # Update payload con historial de especialistas
        specialists_history = current_payload.get("specialists_history", [])
        if last_specialist and last_specialist not in specialists_history:
            specialists_history.append(last_specialist)

        state["payload"] = {
            **current_payload,
            "specialists_history": specialists_history,
            "last_specialist": last_specialist,
        }

        logger.info(f"Chain router: historial de especialistas: {specialists_history}")
        return state

    def _decide_chain_next_node(
        self, state: GraphStateV2, all_specialists: list
    ) -> str:
        """
        Decisión de chaining: determina el siguiente especialista o END.

        Chain Rules (Phase 3B):
        - transcription_agent → planner_agent (para respuesta inteligente)
        - planner_agent → END (respuesta final al usuario)
        - error_state → END
        """
        if state.get("error_message"):
            logger.error("Error en estado, finalizando chain")
            return "__end__"

        payload = state.get("payload", {})
        last_specialist = payload.get("last_specialist")
        next_action = payload.get("next_action")
        specialists_history = payload.get("specialists_history", [])

        logger.info(
            f"Chain decision: last={last_specialist}, action={next_action}, history={specialists_history}"
        )

        # Rule 1: transcription_agent → planner_agent (UX crítico fix)
        if last_specialist == "transcription_agent":
            if "planner_agent" not in specialists_history:
                logger.info("Chain: Transcripción → Planner para respuesta inteligente")
                return "planner_agent"

        # Rule 2: planner_agent → END (respuesta final)
        if last_specialist == "planner_agent" or next_action == "respond_to_user":
            logger.info("Chain: Planner completado → END para responder usuario")
            return "__end__"

        # Rule 3: Fallback → END
        logger.info("Chain: No hay más especialistas, finalizando")
        return "__end__"

    async def run(self, initial_state: GraphStateV2) -> dict:
        """
        Ejecuta el grafo del orquestador principal.
        """
        if not self.graph:
            logger.error("El grafo del MasterOrchestrator no está disponible.")
            initial_state["error_message"] = (
                "El orquestador principal no está disponible."
            )
            return dict(initial_state)

        final_state_dict = await self.graph.ainvoke(initial_state)
        return cast(dict, final_state_dict)


# Instancia única del orquestador para ser reutilizada
master_orchestrator = MasterOrchestrator()
