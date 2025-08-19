# src/agents/orchestrator.py
import logging
from typing import Any, cast

from langgraph.graph import END, StateGraph

from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV1

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
        Construye dinámicamente el grafo de enrutamiento principal
        basándose en los especialistas registrados.
        """
        graph_builder = StateGraph(GraphStateV1)

        # 1. Nodo de entrada: Meta-enrutador basado en capacidades.
        graph_builder.add_node("meta_router", self._meta_route_request)

        # 2. Nodos de especialistas: un nodo por cada especialista.
        all_specialists = specialist_registry.get_all_specialists()
        for specialist in all_specialists:
            compiled_graph = cast(Any, specialist.graph)
            graph_builder.add_node(specialist.name, compiled_graph.ainvoke)
            graph_builder.add_edge(specialist.name, END)

        # 3. Lógica de enrutamiento condicional desde el meta-enrutador.
        graph_builder.set_entry_point("meta_router")

        def router_function(state: GraphStateV1) -> str:
            """Función de enrutamiento que devuelve el nombre del siguiente nodo o END."""
            decision = self._decide_next_node(state)
            # El valor de retorno debe ser uno de los nodos registrados o END
            if decision not in {s.name for s in all_specialists}:
                return "__end__"
            return decision

        graph_builder.add_conditional_edges(
            "meta_router",
            router_function,
        )

        return graph_builder.compile()

    async def _meta_route_request(self, state: GraphStateV1) -> GraphStateV1:
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

    def _decide_next_node(self, state: GraphStateV1) -> str:
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

    async def run(self, initial_state: GraphStateV1) -> dict:
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
