
import logging
from typing import Any, cast
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.core.engine import create_observable_config, llm
from src.tools.google_file_search import file_search_tool
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2, V2ChatMessage
from src.memory.long_term_memory import long_term_memory
from src.core.profile_manager import user_profile_manager
from src.agents.specialists.planner.state_utils import (
    extract_user_content_from_state,
    build_conversation_summary,
)

logger = logging.getLogger(__name__)

# --- Managed Prompts ---
def load_prompt(filename: str) -> str:
    try:
        # Intentar múltiples rutas posibles
        paths = [
            Path(__file__).resolve().parent.parent.parent.parent / "prompts" / filename,
            Path(__file__).resolve().parent.parent.parent.parent / "src" / "prompts" / filename,
            Path("/Users/jhomc/Proyectos/AEGEN/prompts") / filename,
            Path("/Users/jhomc/Proyectos/AEGEN/src/prompts") / filename
        ]
        from pathlib import Path
        for p in paths:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
        logger.error(f"Prompt file not found: {filename}")
        return "Eres MAGI, un asistente estoico. Ayuda al usuario con su trading."
    except Exception as e:
        logger.error(f"Error loading prompt {filename}: {e}")
        return "Error loading prompt. Using fallback."

from pathlib import Path
CBT_THERAPEUTIC_TEMPLATE = load_prompt("cbt_therapeutic_response.txt")

# Keywords que activan el CBT specialist
CBT_KEYWORDS = {
    "spanish": ["ansiedad", "fomo", "disciplina", "ira", "miedo", "pánico", "venganza", "pérdida", "trading", "psicología"],
    "english": ["anxiety", "fomo", "discipline", "anger", "fear", "panic", "revenge", "loss", "trading", "psychology"],
}

@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    conversation_history: str = "",
    analysis_context: str | None = None,
) -> str:
    """Proporciona guía terapéutica basada en CBT y perfil evolutivo."""
    logger.info(f"CBT Tool procesando: '{user_message[:50]}...'")
    try:
        # Mock chat_id if not present
        chat_id = "default_user"
        knowledge_context = await _get_knowledge_context(user_message, chat_id)
        return await _generate_therapeutic_response(
            user_message, conversation_history, knowledge_context, "Resumen no disponible", user_name="Usuario"
        )
    except Exception as e:
        logger.error(f"Error in cbt_tool: {e}")
        return f"Error en el especialista: {str(e)}"

async def _get_knowledge_context(user_message: str, chat_id: str) -> str:
    """Obtiene contexto usando Smart RAG basado en tags del perfil."""
    profile = await user_profile_manager.load_profile()
    active_tags = user_profile_manager.get_active_tags()
    return await file_search_tool.query_files(user_message, chat_id, tags=active_tags)

async def _generate_therapeutic_response(
    user_message: str,
    conversation_history: str,
    knowledge_context: str,
    history_summary: str,
    user_name: str = "Usuario",
    analysis_context: str | None = None,
) -> str:
    """Genera respuesta con alma evolutiva e instrucción de tiempo invisible."""
    profile = await user_profile_manager.load_profile()
    style = user_profile_manager.get_style()
    metrics = profile.get("metrics", {})
    
    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        chain = ChatPromptTemplate.from_template(CBT_THERAPEUTIC_TEMPLATE) | llm

        # Inyección Temporal Invisible v0.3.1
        current_date_str = datetime.now().strftime("%A, %d de %B de %Y")
        invisible_date_hint = f"\n[System Note: Today is {current_date_str}. Use this SILENTLY to log milestones. DO NOT mention the date unless asked.]\n"

        prompt_input = {
            "user_name": user_name,
            "current_date": current_date_str + invisible_date_hint,
            "user_message": user_message,
            "conversation_history": conversation_history,
            "knowledge_context": knowledge_context,
            "history_summary": history_summary,
            "user_style": style,
            "volatility": metrics.get("emotional_volatility", 0.5)
        }

        if analysis_context:
            prompt_input["analysis_context"] = analysis_context

        response = await chain.ainvoke(prompt_input, config=cast(RunnableConfig, config))
        return str(response.content).strip()
    except Exception as e:
        logger.error(f"Error in _generate_therapeutic_response: {e}")
        return "Mantén la disciplina. ¿Qué está bajo tu control ahora?"

async def _cbt_node(state: GraphStateV2) -> GraphStateV2:
    """Nodo principal integrado con Perfil JSON y Smart RAG."""
    logger.info("CBT Node (Evolving Soul v0.3.1) procesando...")
    
    user_content = extract_user_content_from_state(state)
    if not user_content:
        return state
        
    chat_id = state.get("session_id", "default_user")
    user_name = state.get("payload", {}).get("user_name", "Usuario")
    
    # 1. Recuperar Contexto Histórico
    history_data = await long_term_memory.get_summary(chat_id)
    history_summary = history_data.get("summary", "")
    conv_history = build_conversation_summary(state.get("conversation_history", []), max_messages=5)

    # 2. Smart RAG
    knowledge_context = await _get_knowledge_context(user_content, chat_id)

    # 3. Respuesta
    response = await _generate_therapeutic_response(
        user_content, conv_history, knowledge_context, history_summary, user_name=user_name
    )

    # 4. Update State
    state["payload"]["response"] = response
    state["payload"]["last_specialist"] = "cbt_specialist"
    state["payload"]["next_action"] = "respond_to_user"
    
    return state

class CBTSpecialist(SpecialistInterface):
    def __init__(self):
        self._name = "cbt_specialist"
        self._graph = self._build_graph()
        self._tool = cbt_therapeutic_guidance_tool

    @property
    def name(self) -> str: return self._name
    @property
    def graph(self) -> Any: return self._graph
    @property
    def tool(self) -> BaseTool: return self._tool

    def _build_graph(self) -> Any:
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("cbt_therapy", _cbt_node)
        graph_builder.set_entry_point("cbt_therapy")
        graph_builder.add_edge("cbt_therapy", END)
        return graph_builder.compile()

    def can_handle_message(self, message: str, context: dict = None) -> bool:
        text_lower = message.lower()
        return any(k in text_lower for lang in CBT_KEYWORDS.values() for k in lang)

# Registro
specialist_registry.register(CBTSpecialist())
logger.info("🧠 CBT Specialist (Evolving Soul) registered.")
