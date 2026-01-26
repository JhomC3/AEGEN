# src/agents/specialists/chat_agent.py
"""
MAGI: El Asistente Conversacional Principal de AEGEN.
Maneja la interacción directa con el usuario, integrando memoria y perfil psicológico.
"""

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import aiofiles
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.agents.utils.state_utils import extract_user_content_from_state
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.profile_manager import user_profile_manager
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.memory.long_term_memory import long_term_memory
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


def _load_persona_prompt() -> str:
    """Carga el prompt maestro de personalidad (TCC compatible)."""
    try:
        prompt_path = Path("src/prompts/cbt_therapeutic_response.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error cargando persona prompt: {e}")
    return "Eres MAGI, un asistente útil y empático. Usuario: {user_name}. Mensaje: {user_message}."


@tool
async def conversational_chat_tool(
    user_message: str,
    chat_id: str,
    conversation_history: str = "",
    image_path: str | None = None,
) -> str:
    """
    Genera una respuesta empática y contextual usando el perfil del usuario.
    """
    # 1. Cargar perfil (Diskless/Multi-user)
    profile = await user_profile_manager.load_profile(chat_id)
    profile_context = user_profile_manager.get_context_for_prompt(profile)
    style = user_profile_manager.get_style(profile)

    # 2. Smart RAG
    try:
        active_tags = user_profile_manager.get_active_tags(profile)
        knowledge_context = await file_search_tool.query_files(
            user_message, chat_id, tags=active_tags
        )
    except Exception:
        knowledge_context = ""

    # Memoria de Largo Plazo
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Perfil activo.")

    current_date_str = datetime.now().strftime("%A, %d de %B")

    persona_template = _load_persona_prompt()
    conversational_prompt = ChatPromptTemplate.from_template(persona_template)

    prompt_input = {
        "user_name": "Usuario",
        "current_date": current_date_str,
        "user_message": user_message,
        "conversation_history": conversation_history,
        "knowledge_context": knowledge_context,
        "history_summary": history_summary,
        "user_style": style,
        "user_phase": profile_context.get("phase", "Building"),
        "struggles": profile_context.get("struggles", "None"),
        "key_metaphors": profile_context.get("metaphors", "None"),
    }

    try:
        config = create_observable_config(call_type="chat_response")

        if image_path and Path(image_path).exists():
            async with aiofiles.open(image_path, "rb") as f:
                image_data = base64.b64encode(await f.read()).decode("utf-8")
            formatted_prompt = await conversational_prompt.aformat(**prompt_input)
            content_list = [
                {"type": "text", "text": formatted_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                },
            ]
            response = await llm.ainvoke(
                [HumanMessage(content=cast(Any, content_list))],
                config=cast(RunnableConfig, config),
            )
        else:
            chain = conversational_prompt | llm
            response = await chain.ainvoke(
                prompt_input, config=cast(RunnableConfig, config)
            )

        return str(response.content).strip()
    except Exception as e:
        logger.error(f"Error en MAGI chat: {e}")
        return "Lo siento, tuve un problema interno. ¿Podemos intentarlo de nuevo?"


async def _chat_node(state: GraphStateV2) -> Any:
    """Nodo LangGraph para el chat principal."""
    user_content = extract_user_content_from_state(state)
    if not user_content:
        return state

    chat_id = state.get("session_id", "default_user")
    raw_history = state.get("conversation_history", [])

    # Formatear historial reciente para el LLM
    history_text = "\n".join([
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
        for m in raw_history[-8:]
    ])

    image_path = state.get("payload", {}).get("image_file_path")

    response_text = await conversational_chat_tool.ainvoke({
        "user_message": user_content,
        "chat_id": chat_id,
        "conversation_history": history_text,
        "image_path": image_path,
    })

    # Persistencia en memoria infinita
    await long_term_memory.store_raw_message(chat_id, "user", user_content)
    await long_term_memory.store_raw_message(chat_id, "assistant", response_text)

    # Actualizar historial de sesión
    updated_history = list(raw_history)
    updated_history.append({"role": "user", "content": user_content})
    updated_history.append({"role": "assistant", "content": response_text})

    state["payload"]["response"] = response_text
    state["conversation_history"] = updated_history[-20:]
    return state


class ChatSpecialist(SpecialistInterface):
    """Especialista Conversacional (MAGI)."""

    def __init__(self):
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
