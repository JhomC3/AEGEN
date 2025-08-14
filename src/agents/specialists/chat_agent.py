# src/agents/specialists/chat_agent.py
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.core.engine import llm
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

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Eres un asistente de IA conversacional y amigable."),
            ("human", "{user_message}"),
        ]
    )
    # LCEL: LangChain Expression Language
    chain = prompt | llm
    try:
        response = await chain.ainvoke({"user_message": user_message})
        content = response.content
        if not isinstance(content, str):
            raise ValueError("La respuesta del LLM no es un string.")
        return content
    except Exception as e:
        logger.error(f"Error en la herramienta de chat: {e}", exc_info=True)
        return "Lo siento, tuve un problema para procesar tu mensaje."


class ChatSpecialist:
    """
    Agente especializado en conversación general.
    """

    def __init__(self):
        self._name: str = "chat_specialist"
        # TODO: Investigar por qué mypy no encuentra CompiledStateGraph
        self._graph: Any = self._build_graph()
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

    def _build_graph(self) -> Any:
        graph_builder = StateGraph(GraphStateV1)
        graph_builder.add_node("chat", self._chat_node)
        graph_builder.set_entry_point("chat")
        graph_builder.add_edge("chat", END)
        return graph_builder.compile()

    async def _chat_node(self, state: GraphStateV1) -> dict[str, Any]:
        user_message = state.event.content or ""
        result = await self.tool.ainvoke({"user_message": user_message})
        return {"payload": {**state.payload, "response": result}}


# Registrar la instancia del especialista
specialist_registry.register(ChatSpecialist())
