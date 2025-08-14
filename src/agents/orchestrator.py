# src/agents/orchestrator.py
import logging
from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from src.core.engine import llm
from src.core.schemas import GraphStateV1

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    El orquestador central (MasterRouter) que dirige el flujo de trabajo
    basándose en la intención del usuario.
    """

    def __init__(self):
        self.graph: Any = self._build_graph()

    def _decide_next_node(
        self, state: GraphStateV1
    ) -> Literal["transcription", "inventory", "chat", "__end__"]:
        """
        Determina el siguiente nodo basado en la decisión del enrutador.
        """
        route_name = state.payload.get("route_name")
        if route_name == "transcription":
            return "transcription"
        if route_name == "inventory":
            return "inventory"
        if route_name == "chat":
            return "chat"
        return "__end__"

    def _build_graph(self) -> Any:
        """
        Construye el grafo de enrutamiento principal.
        """
        graph_builder = StateGraph(GraphStateV1)

        # --- Definición de Nodos ---
        graph_builder.add_node("router", self._route_request)
        # TODO: Reemplazar placeholders con los agentes especialistas reales.
        graph_builder.add_node("transcription", self._placeholder_node)
        graph_builder.add_node("inventory", self._placeholder_node)
        graph_builder.add_node("chat", self._placeholder_node)

        # --- Definición de Aristas ---
        graph_builder.set_entry_point("router")
        graph_builder.add_conditional_edges(
            "router",
            self._decide_next_node,
            {
                "transcription": "transcription",
                "inventory": "inventory",
                "chat": "chat",
                "__end__": END,
            },
        )
        graph_builder.add_edge("transcription", END)
        graph_builder.add_edge("inventory", END)
        graph_builder.add_edge("chat", END)

        # Compilar el grafo
        return graph_builder.compile()

    async def _route_request(self, state: GraphStateV1) -> dict[str, Any]:
        """
        Clasifica la solicitud del usuario para enrutarla al especialista adecuado.
        """
        user_message = state.event.content or ""
        logger.info(f"Enrutando mensaje del usuario: '{user_message}'")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un experto en enrutar solicitudes de usuario al especialista correcto. "
                    "Las opciones son: 'transcription', 'inventory', 'chat'. "
                    "Si el usuario pide transcribir algo, responde 'transcription'. "
                    "Si el usuario habla de inventario, stock, o excel, responde 'inventory'. "
                    "Para cualquier otra conversación, responde 'chat'. "
                    "Responde únicamente con una de esas tres palabras.",
                ),
                ("human", "Mensaje del usuario: '{user_message}'"),
            ]
        )

        router_chain = prompt | llm
        try:
            route = await router_chain.ainvoke({"user_message": user_message})
            content = route.content
            if not isinstance(content, str):
                raise ValueError("La respuesta del enrutador no es un string.")
            route_name = content.strip().lower()
            logger.info(f"Decisión de enrutamiento: {route_name}")
            return {"payload": {**state.payload, "route_name": route_name}}
        except Exception as e:
            logger.error(f"Error en el enrutamiento: {e}", exc_info=True)
            return {"payload": {**state.payload, "route_name": "error"}}

    async def _placeholder_node(self, state: GraphStateV1) -> dict[str, Any]:
        """Nodo placeholder para especialistas no implementados."""
        route_name = state.payload.get("route_name", "desconocido")
        logger.info(f"Ejecutando nodo placeholder para el especialista: {route_name}")
        return {
            "payload": {
                **state.payload,
                "response": f"Respuesta desde el placeholder del especialista '{route_name}'.",
            }
        }

    async def run(self, initial_state: GraphStateV1) -> GraphStateV1:
        """
        Ejecuta el grafo del orquestador principal.
        """
        if not self.graph:
            logger.error("El grafo del MasterOrchestrator no está implementado.")
            initial_state.error_message = "El orquestador principal no está disponible."
            return initial_state

        final_state_dict = await self.graph.ainvoke(initial_state)
        return GraphStateV1.model_validate(final_state_dict)


# Instancia única del orquestador para ser reutilizada
master_orchestrator = MasterOrchestrator()
