import logging
from datetime import datetime
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

from src.agents.specialists.planner.state_utils import (
    extract_user_content_from_state,
)
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.profile_manager import user_profile_manager
from src.core.prompts.loader import load_text_prompt
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.memory.long_term_memory import long_term_memory

logger = logging.getLogger(__name__)


# Keywords que activan el CBT specialist
CBT_KEYWORDS = {
    "spanish": [
        "ansiedad",
        "fomo",
        "disciplina",
        "ira",
        "miedo",
        "pánico",
        "venganza",
        "pérdida",
        "trading",
        "psicología",
        "triste",
    ],
    "english": [
        "anxiety",
        "fomo",
        "discipline",
        "anger",
        "fear",
        "panic",
        "revenge",
        "loss",
        "trading",
        "psychology",
        "sad",
    ],
}

# --- Managed Prompts ---
CBT_THERAPEUTIC_TEMPLATE = (
    load_text_prompt("cbt_therapeutic_response.txt")
    or "Eres MAGI, un mentor estoico. Ayuda al usuario con su trading sin preguntar la fecha."
)


@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    conversation_history: str = "",
    analysis_context: str | None = None,
) -> str:
    """
    Rescue MAGI v0.3.2
    """
    await user_profile_manager.load_profile()
    style = user_profile_manager.get_style()
    user_profile_manager.get_context_for_prompt()  # phase, metaphors, struggles

    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        chain = ChatPromptTemplate.from_template(CBT_THERAPEUTIC_TEMPLATE) | llm

        # Definimos la Verdad Absoluta Temporal
        current_date_str = datetime.now().strftime("%A, %d de %B de %Y")

        prompt_input = {
            "user_name": "Usuario",
            "current_date": current_date_str,
            "user_message": user_message,
            "conversation_history": conversation_history,
            "analysis_context": analysis_context or "No hay análisis previo.",
            "user_style": style,
        }

        response = await chain.ainvoke(
            prompt_input, config=cast(RunnableConfig, config)
        )
        return str(response.content).strip()

    except Exception as e:
        logger.error(f"Error en CBT tool: {e}")
        return "Respiro hondo. Mantén la calma, el mercado es solo ruido. Cuéntame más sobre lo que sientes."


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
        logger.info("CBT Node (Professional v1.0) procesando...")

        user_content = extract_user_content_from_state(state)
        if not user_content:
            return cast(dict[str, Any], state)

        chat_id = state.get("session_id", "default_user")

        # 1. Recuperar Historial y Perfil
        history_data = await long_term_memory.get_summary(chat_id)
        history_text = history_data.get("summary", "")

        # 2. Ejecutar Tool
        response_text = await self.tool.ainvoke({
            "user_message": user_content,
            "conversation_history": history_text,
            "analysis_context": state.get("payload", {}).get("analysis", ""),
        })

        # 3. Actualizar Estado
        state["payload"]["response"] = response_text
        state["payload"]["last_specialist"] = "cbt_specialist"
        state["payload"]["next_action"] = "respond_to_user"

        return cast(dict[str, Any], state)


# Registro automático
specialist_registry.register(CBTSpecialist())
