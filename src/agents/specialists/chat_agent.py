# src/agents/specialists/chat_agent.py
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.core.engine import llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


@tool
async def conversational_chat_tool(
    user_message: str, conversation_history: str = ""
) -> str:
    """
    Herramienta principal del ChatAgent para respuestas conversacionales directas.

    Arquitectura simplificada: genera respuestas conversacionales naturales
    sin lógica de delegación (routing manejado por Enhanced Router).
    """
    logger.info(f"ChatAgent procesando: '{user_message[:50]}...'")
    
    # Respuesta conversacional directa única
    return await _direct_conversational_response(user_message, conversation_history)


async def _direct_conversational_response(
    user_message: str, conversation_history: str
) -> str:
    """
    Genera respuesta conversacional directa sin delegación.
    """
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Eres AEGEN, un asistente de IA conversacional, inteligente y amigable.

Tu personalidad:
- Eres natural, empático y profesional
- Respondes de manera concisa pero completa
- Mantienes el contexto de la conversación
- Eres proactivo para ayudar al usuario

Contexto conversacional previo:
{conversation_history}

Responde de manera natural y conversacional.""",
        ),
        ("human", "{user_message}"),
    ])

    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "user_message": user_message,
            "conversation_history": conversation_history,
        })
        return str(response.content)
    except Exception as e:
        logger.error(f"Error en respuesta directa: {e}", exc_info=True)
        return "Disculpa, tuve un problema técnico. ¿Podrías intentar de nuevo?"


class ChatSpecialist(SpecialistInterface):
    """
    Agente especializado en conversación general.
    """

    def __init__(self):
        self._name = "chat_specialist"
        self._graph = self._build_graph()
        self._tool: BaseTool = conversational_chat_tool

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
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("chat", self._chat_node)
        graph_builder.set_entry_point("chat")
        graph_builder.add_edge("chat", END)
        return graph_builder.compile()

    async def _chat_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Nodo principal del agente de chat. Valida el estado y ejecuta la herramienta.
        """
        try:
            event_obj = state["event"]
        except KeyError:
            return {"error_message": "El evento no se encontró en el estado."}

        user_message = event_obj.content or ""

        # Build conversation history string from state
        conversation_history = state.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_parts.append(f"{role.capitalize()}: {content}")
            history_text = "\n".join(history_parts)

        result = await self.tool.ainvoke({
            "user_message": user_message,
            "conversation_history": history_text,
        })

        # Update conversation history like PlannerAgent does
        updated_history = list(conversation_history)
        if user_message:
            updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": str(result)})

        current_payload = state.get("payload", {})
        return {
            "payload": {**current_payload, "response": result},
            "conversation_history": updated_history,
        }


# ChatAgent simplificado para responses conversacionales directas
specialist_registry.register(ChatSpecialist())
