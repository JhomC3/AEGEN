import logging
from pathlib import Path
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt
from src.core.dependencies import get_vector_memory_manager
from src.core.engine import create_observable_config, llm
from src.core.message_utils import (
    dict_to_langchain_messages,
    extract_recent_user_messages,
)
from src.core.profile_manager import user_profile_manager
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory
from src.personality.prompt_builder import system_prompt_builder

from .multimodal import process_image_input

logger = logging.getLogger(__name__)


async def _get_chat_rag_context(chat_id: str, user_message: str) -> str:
    """Recupera contexto relevante usando Smart RAG (Global + Usuario)."""
    try:
        manager = get_vector_memory_manager()
        # Buscar en conocimiento global y del usuario
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=2, namespace="global"
        )
        user_results = await manager.retrieve_context(
            user_id=chat_id, query=user_message, limit=2, namespace="user"
        )

        all_results = global_results + user_results

        # Transparencia RAG enriquecida (ADR-0025)
        global_sources = [
            r.get("metadata", {}).get("filename", "?") for r in global_results
        ]
        logger.info(
            f"[CHAT-RAG] Context injection for chat={chat_id}",
            extra={
                "event": "specialist_rag_injection",
                "specialist": "chat",
                "chat_id": chat_id,
                "global_count": len(global_results),
                "user_count": len(user_results),
                "global_sources": global_sources,
            },
        )

        if all_results:
            formatted_results = []
            for r in all_results:
                source = r.get("metadata", {}).get("filename", "Memoria de Usuario")
                formatted_results.append(f"- [Fuente: {source}] {r['content']}")
            return "\n\n".join(formatted_results)
        return ""

    except Exception as e:
        logger.warning(f"Error en RAG Chat: {e}")
        return ""


async def _get_chat_memories(chat_id: str) -> tuple[str, str]:
    """Recupera resumen de memoria y conocimiento estructurado."""
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Perfil activo.")

    knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
    structured_knowledge = format_knowledge_for_prompt(knowledge_data)
    return history_summary, structured_knowledge


@tool
async def conversational_chat_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    image_path: str | None = None,
    routing_metadata: dict[str, Any] | None = None,
    session_context: dict[str, Any] | None = None,
) -> str:
    """
    Genera una respuesta empática y contextual usando el perfil del usuario.
    """
    if conversation_history is None:
        conversation_history = []

    routing_metadata = routing_metadata or {}
    session_context = session_context or {}
    next_actions = routing_metadata.get("next_actions", [])

    # 1. Cargar perfil y Contexto (RAG + Memoria)
    profile = await user_profile_manager.load_profile(chat_id)
    knowledge_context = await _get_chat_rag_context(chat_id, user_message)
    history_summary, structured_knowledge = await _get_chat_memories(chat_id)

    # 2. Configurar Persona y Prompts
    adaptation = user_profile_manager.get_personality_adaptation(profile)
    history_limit = adaptation.get("history_limit", 20)
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

    # Extraer is_proactive y pending_intents
    is_proactive = session_context.get("is_proactive", False)
    pending_intents = session_context.get("pending_intents", [])

    persona_template = await system_prompt_builder.build(
        chat_id=chat_id,
        profile=profile,
        skill_name="chat",
        runtime_context={
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
            "is_proactive": is_proactive,
            "pending_intents": pending_intents,
        },
        recent_user_messages=extract_recent_user_messages(messages),
    )

    # Inyección de instrucciones de enrutamiento
    if "monitor_emotional_cues" in next_actions:
        persona_template += (
            "\n\nAVISO DE ENRUTAMIENTO: Se han detectado señales sutiles de "
            "vulnerabilidad. Mantén un tono empático y valida sus sentimientos "
            "si parece necesario, pero sin forzar una conversación profunda.\n"
        )

    conversational_prompt = ChatPromptTemplate.from_messages([
        ("system", persona_template),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "{user_message}"),
    ])

    # 3. Ejecución
    try:
        prompt_input = {"user_message": user_message, "messages": messages}
        config = create_observable_config(call_type="chat_response")

        if image_path and Path(image_path).exists():
            return await process_image_input(
                image_path,
                prompt_input,
                conversational_prompt,
                cast(RunnableConfig, config),
            )

        chain = conversational_prompt | llm
        response = await chain.ainvoke(
            prompt_input, config=cast(RunnableConfig, config)
        )
        return str(response.content).strip()
    except Exception as e:
        logger.error(f"Error en MAGI chat: {e}")
        return "Lo siento, tuve un problema interno. ¿Reintentamos?"
