# src/agents/specialists/chat_agent.py
"""
MAGI: El Asistente Conversacional Principal de AEGEN.
Maneja la interacción directa con el usuario, integrando memoria y perfil psicológico.
"""

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from src.agents.specialists.chat.chat_tool import conversational_chat_tool
from src.agents.utils.state_utils import extract_user_content_from_state
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


async def _chat_node(state: GraphStateV2) -> Any:
    """Nodo LangGraph para el chat principal."""
    user_content = extract_user_content_from_state(state)
    if not user_content:
        return state

    chat_id = state.get("session_id", "default_user")
    raw_history = state.get("conversation_history", [])

    payload = state.get("payload", {})
    image_path = payload.get("image_file_path")
    routing_decision = payload.get("routing_decision", {})
    session_ctx = payload.get("session_context", {})
    cbt_plan_json = payload.get("cbt_plan_json")

    response_text = await conversational_chat_tool.ainvoke({
        "user_message": user_content,
        "chat_id": chat_id,
        "conversation_history": raw_history,
        "image_path": image_path,
        "routing_metadata": routing_decision,
        "session_context": session_ctx,
        "cbt_plan_json": cbt_plan_json,
    })

    # Actualizar historial de sesión
    updated_history = list(raw_history)
    updated_history.append({"role": "user", "content": user_content})
    updated_history.append({"role": "assistant", "content": response_text})

    state["payload"]["response"] = response_text
    state["payload"]["last_specialist"] = "chat_specialist"
    state["payload"]["next_action"] = "respond_to_user"
    state["conversation_history"] = updated_history[-20:]
    return state


class ChatSpecialist(SpecialistInterface):
    """Especialista Conversacional (MAGI)."""

    def __init__(self) -> None:
        self._name = "chat_specialist"
        self._tool = conversational_chat_tool
        self._graph = self._build_graph()

    @property
    def name(self) -> str:
        return self._name

    @property
    def tool(self) -> BaseTool:
        return self._tool

    @property
    def graph(self) -> Any:
        return self._graph

    def get_capabilities(self) -> list[str]:
        return ["text", "conversation", "multimodal"]

    def _build_graph(self) -> Any:
        builder = StateGraph(GraphStateV2)
        builder.add_node("chat", _chat_node)
        builder.set_entry_point("chat")
        builder.add_edge("chat", END)
        return builder.compile()


specialist_registry.register(ChatSpecialist())
