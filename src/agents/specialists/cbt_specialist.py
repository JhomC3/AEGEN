import logging
from typing import Any, cast

from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph

from src.agents.specialists.cbt.cbt_tool import cbt_therapeutic_guidance_tool
from src.agents.utils.state_utils import (
    extract_user_content_from_state,
)
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


class CBTSpecialist(SpecialistInterface):
    """
    Especialista en Terapia Cognitivo Conductual (CBT).
    """

    def __init__(self):
        self._name = "cbt_specialist"
        self._tool = cbt_therapeutic_guidance_tool
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
        return ["cbt", "psychology", "emotional_support"]

    def _build_graph(self) -> Any:
        workflow = StateGraph(GraphStateV2)
        workflow.add_node("cbt_node", self._cbt_node)
        workflow.set_entry_point("cbt_node")
        return workflow.compile()

    async def _cbt_node(self, state: GraphStateV2) -> dict[str, Any]:
        """Nodo principal CBT - Professional Clinical Psychologist"""
        logger.info("CBT Node procesando...")

        user_content = extract_user_content_from_state(state)
        if not user_content:
            return cast(dict[str, Any], state)

        chat_id = state.get("session_id", "default_user")

        # Formatear historial para el prompt (mensajes recientes)
        raw_history = state.get("conversation_history", [])

        # 2. Ejecutar Tool
        routing_decision = state.get("payload", {}).get("routing_decision", {})

        response_text = await self.tool.ainvoke({
            "user_message": user_content,
            "chat_id": chat_id,
            "conversation_history": raw_history,
            "routing_metadata": routing_decision,
        })

        # 3. Actualizar Estado
        state["payload"]["response"] = response_text
        state["payload"]["last_specialist"] = "cbt_specialist"
        state["payload"]["next_action"] = "respond_to_user"

        return cast(dict[str, Any], state)


# Registro automático
specialist_registry.register(CBTSpecialist())
