import logging
from datetime import datetime
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

from src.agents.utils.state_utils import (
    extract_user_content_from_state,
)
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.profile_manager import user_profile_manager
from src.core.prompts.loader import load_text_prompt
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.memory.long_term_memory import long_term_memory
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)

# --- Managed Prompts ---
CBT_THERAPEUTIC_TEMPLATE = (
    load_text_prompt("cbt_therapeutic_response.txt")
    or "Eres MAGI, un mentor estoico. Ayuda al usuario con su trading sin preguntar la fecha."
)


@tool
async def query_user_history(chat_id: str, query: str) -> str:
    """
    5.2: Consulta el historial profundo del usuario para recuperar detalles del pasado.
    Útil para recordar metas, valores o eventos conversados hace mucho tiempo.
    """
    return await file_search_tool.search_user_history(chat_id, query)


@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    chat_id: str,
    conversation_history: str = "",
) -> str:
    """
    Ejecuta la guía terapéutica TCC inyectando el perfil completo del usuario.
    """
    # 1. Cargar perfil (Diskless/Multi-user)
    profile = await user_profile_manager.load_profile(chat_id)
    profile_context = user_profile_manager.get_context_for_prompt(profile)
    style = user_profile_manager.get_style(profile)

    # 2. Recuperar Memoria de Largo Plazo (Resumen)
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Sin historial previo.")

    # 3. Smart RAG (Conocimiento TCC)
    try:
        active_tags = user_profile_manager.get_active_tags(profile)
        knowledge_context = await file_search_tool.query_files(
            user_message, chat_id, tags=active_tags
        )
    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        knowledge_context = "No hay contexto documental disponible."

    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        chain = ChatPromptTemplate.from_template(CBT_THERAPEUTIC_TEMPLATE) | llm

        current_date_str = datetime.now().strftime("%A, %d de %B de %Y")

        prompt_input = {
            "current_date": current_date_str,
            "user_message": user_message,
            "conversation_history": conversation_history,
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "user_style": style,
            "user_phase": profile_context.get("phase", "Unknown"),
            "struggles": profile_context.get("struggles", "None"),
            "key_metaphors": profile_context.get("metaphors", "None"),
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
        logger.info("CBT Node procesando...")

        user_content = extract_user_content_from_state(state)
        if not user_content:
            return cast(dict[str, Any], state)

        chat_id = state.get("session_id", "default_user")

        # Formatear historial para el prompt (mensajes recientes)
        raw_history = state.get("conversation_history", [])
        history_text = "\n".join([
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in raw_history[-5:]
        ])

        # 2. Ejecutar Tool
        response_text = await self.tool.ainvoke({
            "user_message": user_content,
            "chat_id": chat_id,
            "conversation_history": history_text,
        })

        # 3. Actualizar Estado
        state["payload"]["response"] = response_text
        state["payload"]["last_specialist"] = "cbt_specialist"
        state["payload"]["next_action"] = "respond_to_user"

        return cast(dict[str, Any], state)


# Registro automático
specialist_registry.register(CBTSpecialist())
