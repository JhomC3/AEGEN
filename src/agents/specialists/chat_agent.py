# src/agents/specialists/chat_agent.py
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.core.engine import llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV1

logger = logging.getLogger(__name__)


@tool
async def chat_tool(user_message: str) -> str:
    """
    Usa esta herramienta para conversaciones generales, saludos o cualquier
    solicitud que no se ajuste a otras herramientas especializadas.
    """
    logger.info(f"Herramienta de chat procesando: '{user_message}'")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente de IA conversacional y amigable."),
        ("human", "{user_message}"),
    ])
    chain = prompt | llm
    try:
        response = await chain.ainvoke({"user_message": user_message})
        return str(response.content)  # type: ignore [no-any-return]
    except Exception as e:
        logger.error(f"Error en la herramienta de chat: {e}", exc_info=True)
        return "Lo siento, tuve un problema para procesar tu mensaje."


class ChatSpecialist(SpecialistInterface):
    """
    Agente especializado en conversación general.
    """

    def __init__(self):
        self._name = "chat_specialist"
        self._graph = self._build_graph()
        self._tool: BaseTool = chat_tool

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Any:
        return self._graph

    @property
    def tool(self) -> BaseTool:
        return self._tool

    def get_capabilities(self) -> list[str]:
        """Este agente maneja eventos de texto plano."""
        return ["text"]

    def _build_graph(self) -> Any:
        graph_builder = StateGraph(GraphStateV1)
        graph_builder.add_node("chat", self._chat_node)
        graph_builder.set_entry_point("chat")
        graph_builder.add_edge("chat", END)
        return graph_builder.compile()

    async def _chat_node(self, state: GraphStateV1) -> dict[str, Any]:
        """
        Nodo principal del agente de chat. Valida el estado y ejecuta la herramienta.
        """
        try:
            event_obj = state["event"]
        except KeyError:
            return {"error_message": "El evento no se encontró en el estado."}

        user_message = event_obj.content or ""
        result = await self.tool.ainvoke({"user_message": user_message})

        current_payload = state.get("payload", {})
        return {"payload": {**current_payload, "response": result}}


# Registrar la instancia del especialista
specialist_registry.register(ChatSpecialist())
