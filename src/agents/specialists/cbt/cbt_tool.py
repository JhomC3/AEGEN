import logging
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

from .prompt_builder import (
    CLINICAL_GUARDRAILS,
    build_enriched_profile_context,
    build_routing_instructions,
)

logger = logging.getLogger(__name__)


async def _get_cbt_rag_context(chat_id: str, user_message: str) -> str:
    """Recupera contexto TCC relevante usando Smart RAG."""
    try:
        manager = get_vector_memory_manager()
        # Buscar en conocimiento global (TCC) y del usuario
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=3, namespace="global"
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
            f"[CBT-RAG] Context injection for chat={chat_id}",
            extra={
                "event": "specialist_rag_injection",
                "specialist": "cbt",
                "chat_id": chat_id,
                "global_count": len(global_results),
                "user_count": len(user_results),
                "global_sources": global_sources,
                "total_context_chars": sum(len(r["content"]) for r in all_results),
            },
        )

        if all_results:
            return "\n\n".join([f"- {r['content']}" for r in all_results])
        return "No hay contexto documental disponible."

    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        return "No hay contexto documental disponible."


async def _get_cbt_memories(chat_id: str) -> tuple[str, str]:
    """Recupera resumen de memoria y hechos para CBT."""
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Sin historial previo.")

    knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
    structured_knowledge = format_knowledge_for_prompt(knowledge_data)
    return history_summary, structured_knowledge


@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    routing_metadata: dict[str, Any] | None = None,
) -> str:
    """
    Ejecuta la guía terapéutica TCC inyectando el perfil completo del usuario.
    """
    if conversation_history is None:
        conversation_history = []

    routing_metadata = routing_metadata or {}
    next_actions = routing_metadata.get("next_actions", [])

    # 1. Cargar perfil y Contexto (RAG + Memoria)
    profile = await user_profile_manager.load_profile(chat_id)
    knowledge_context = await _get_cbt_rag_context(chat_id, user_message)
    history_summary, structured_knowledge = await _get_cbt_memories(chat_id)

    # 2. Configurar Persona y Prompts
    adaptation = user_profile_manager.get_personality_adaptation(profile)
    history_limit = adaptation.get("history_limit", 20)
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

    persona_template = await system_prompt_builder.build(
        chat_id=chat_id,
        profile=profile,
        skill_name="tcc",
        runtime_context={
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
        recent_user_messages=extract_recent_user_messages(messages),
    )

    # 3. Inyecciones Adicionales (Enriquecimiento + Guardrails + Routing)
    enriched_context = build_enriched_profile_context(profile)
    if enriched_context:
        persona_template += f"\n\n{enriched_context}"

    persona_template += CLINICAL_GUARDRAILS

    routing_instructions = build_routing_instructions(next_actions)
    if routing_instructions:
        persona_template += routing_instructions

    # 4. Ejecución
    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        conversational_prompt = ChatPromptTemplate.from_messages([
            ("system", persona_template),
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{user_message}"),
        ])

        chain = conversational_prompt | llm
        response = await chain.ainvoke(
            {"user_message": user_message, "messages": messages},
            config=cast(RunnableConfig, config),
        )
        return str(response.content).strip()

    except Exception as e:
        logger.error(f"Error en CBT tool: {e}")
        return (
            "Respiro hondo. Mantén la calma, el mercado es solo ruido. "
            "Cuéntame más sobre lo que sientes."
        )
