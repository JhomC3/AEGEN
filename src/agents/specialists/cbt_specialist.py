
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
        from pathlib import Path
        # Intentar múltiples rutas posibles
        paths = [
            Path(__file__).resolve().parent.parent.parent.parent / "prompts" / filename,
            Path(__file__).resolve().parent.parent.parent.parent / "src" / "prompts" / filename,
            Path("/Users/jhomc/Proyectos/AEGEN/prompts") / filename,
            Path("/Users/jhomc/Proyectos/AEGEN/src/prompts") / filename
        ]
        for p in paths:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
        logger.error(f"Prompt file not found: {filename}")
        return "Eres MAGI, un mentor estoico. Ayuda al usuario con su trading sin preguntar la fecha."
    except Exception as e:
        logger.error(f"Error loading prompt {filename}: {e}")
        return "Error loading prompt. Using fallback."

from pathlib import Path
CBT_THERAPEUTIC_TEMPLATE = load_prompt("cbt_therapeutic_response.txt")

# Keywords que activan el CBT specialist
CBT_KEYWORDS = {
    "spanish": ["ansiedad", "fomo", "disciplina", "ira", "miedo", "pánico", "venganza", "pérdida", "trading", "psicología", "triste"],
    "english": ["anxiety", "fomo", "discipline", "anger", "fear", "panic", "revenge", "loss", "trading", "psychology", "sad"],
}

@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    conversation_history: str = "",
    analysis_context: str | None = None,
) -> str:
    """Proporciona guía estoica basada en perfil evolutivo (v0.3.2)."""
    logger.info(f"CBT Tool procesando: '{user_message[:50]}...'")
    try:
        chat_id = "default_user"
        knowledge_context = await _get_knowledge_context(user_message, chat_id)
        return await _generate_therapeutic_response(
            user_message, conversation_history, knowledge_context, "Resumen no disponible", user_name="Usuario"
        )
    except Exception as e:
        logger.error(f"Error in cbt_tool: {e}")
        return f"Error en el especialista: {str(e)}"

async def _get_knowledge_context(user_message: str, chat_id: str) -> str:
    """Smart RAG v0.3.2: Retrieval basado en tags del perfil."""
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
    """
    Genera respuesta con persona 'Mentor Estoico' y ancla temporal absoluta.
    Rescue MAGI v0.3.2
    """
    profile = await user_profile_manager.load_profile()
    style = user_profile_manager.get_style()
    context_keys = user_profile_manager.get_context_for_prompt() # phase, metaphors, struggles
    
    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        chain = ChatPromptTemplate.from_template(CBT_THERAPEUTIC_TEMPLATE) | llm

        # --- TIME-LOCK PROTOCOL (v0.3.2) ---
        # Definimos la Verdad Absoluta Temporal
        current_date_str = datetime.now().strftime("%A, %d de %B de %Y")
        
        prompt_input = {
            "user_name": user_name,
            "current_date": current_date_str, # Se inyecta sin tags, el prompt tiene la orden de no preguntar
            "user_message": user_message,
            "conversation_history": conversation_history,
            "knowledge_context": knowledge_context,
            "history_summary": history_summary,
            "user_phase": context_keys.get("phase", "Unknown"),
            "key_metaphors": context_keys.get("metaphors", ""),
            "struggles": context_keys.get("struggles", "")
        }

        if analysis_context:
            prompt_input["analysis_context"] = analysis_context

        response = await chain.ainvoke(prompt_input, config=cast(RunnableConfig, config))
        return str(response.content).strip()
    except Exception as e:
        logger.error(f"Error in _generate_therapeutic_response: {e}")
        return "El mercado es incertidumbre. Tu disciplina es la única certeza. Mantente firme."

async def _cbt_node(state: GraphStateV2) -> GraphStateV2:
    """Nodo principal CBT - Rescue MAGI v0.3.2"""
    logger.info("CBT Node (Deep Stoic v0.3.2) procesando...")
    
    user_content = extract_user_content_from_state(state)
    if not user_content:
        return state
        
    chat_id = state.get("session_id", "default_user")
    user_name = state.get("payload", {}).get("user_name", "Usuario")
    
    # 1. Recuperar Historial y Perfil
    history_data = await long_term_memory.get_summary(chat_id)
    history_summary = history_data.get("summary", "")
    conv_history = build_conversation_summary(state.get("conversation_history", []), max_messages=5)

    # 2. Smart RAG
    knowledge_context = await _get_knowledge_context(user_content, chat_id)

    # 3. Generar Respuesta Mentoral
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
logger.info("🧠 CBT Specialist (Rescue MAGI v0.3.2) registered.")
