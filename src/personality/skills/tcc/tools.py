import logging
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt
from src.core.crisis_detector import detect_crisis
from src.core.dependencies import get_vector_memory_manager
from src.core.engine import create_observable_config
from src.core.message_utils import (
    dict_to_langchain_messages,
    extract_recent_user_messages,
)
from src.core.profile_manager import user_profile_manager
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory
from src.personality.prompt_builder import system_prompt_builder
from src.personality.skills.tcc.prompt_builder import (
    CLINICAL_GUARDRAILS,
    build_enriched_profile_context,
    build_routing_instructions,
)

logger = logging.getLogger(__name__)


async def _get_cbt_rag_context(chat_id: str, user_message: str) -> str:
    """Recupera contexto TCC relevante usando Smart RAG."""
    try:
        manager = get_vector_memory_manager()
        # Buscar en conocimiento global (TCC) y del usuario filtrando por tipos válidos
        allowed_types = ["fact", "document"]
        global_results = await manager.retrieve_context(
            user_id="system",
            query=user_message,
            limit=3,
            namespace="global",
            context_type=allowed_types,
        )
        user_results = await manager.retrieve_context(
            user_id=chat_id,
            query=user_message,
            limit=2,
            namespace=f"user_{chat_id}",
            context_type=allowed_types,
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
    rag_context: dict[str, Any] | None = None,
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

    # Si viene precargado en rag_context del orquestador, lo usamos.
    if rag_context:
        logger.info("[CBT-RAG] Reusing RAG context snapshot from graphstate")
        semantic_fragments = rag_context.get("semantic_fragments", [])
        evolution_note = rag_context.get("evolution_note", "Sin historial previo.")

        # Formatear structured_facts de forma robusta
        facts_list = rag_context.get("structured_facts", [])
        # Formatear como string simple key=value, evitando
        # format_knowledge_for_prompt que espera estructura de vault
        facts_parts = []
        for f in facts_list:
            k = f.get("key", "")
            v = f.get("value", "")
            if k and v and not k.startswith("_"):
                facts_parts.append(f"- {k}: {v}")
        structured_knowledge = (
            "\n".join(facts_parts) if facts_parts else "No hay hechos confirmados aún."
        )
    else:
        # Fallback por compatibilidad directa o testing aislado
        semantic_fragments = await get_vector_memory_manager().retrieve_context(
            user_id=chat_id,
            query=user_message,
            limit=3,
            namespace=f"user_{chat_id}",
            context_type=["fact", "document"],
        )
        evolution_note_data = await long_term_memory.get_summary(chat_id)
        evolution_note = evolution_note_data.get("summary", "Sin historial previo.")
        knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
        structured_knowledge = format_knowledge_for_prompt(knowledge_data)

    knowledge_context = (
        "\n\n".join([f"- {r['content']}" for r in semantic_fragments])
        if semantic_fragments
        else "No hay contexto documental disponible."
    )

    # 2. Configurar Persona y Prompts
    adaptation = user_profile_manager.get_personality_adaptation(profile)
    # Reducido a 5 interacciones (10 mensajes) para no superar límite TPM de Groq
    history_limit = adaptation.get("history_limit", 5)
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

    persona_messages = await system_prompt_builder.build(
        profile=profile,
        skill_name="tcc",
        runtime_context={
            "history_summary": evolution_note,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
        recent_user_messages=extract_recent_user_messages(messages),
    )

    # 3. Inyecciones Adicionales (Enriquecimiento + Guardrails + Routing)
    enriched_context = build_enriched_profile_context(profile)
    if enriched_context:
        persona_messages.append(("system", enriched_context))

    crisis_result = detect_crisis(user_message)
    if crisis_result["is_crisis"]:
        logger.info(
            "[CBT-GUARDRAILS] Crisis detected: level=%s, confidence=%.2f",
            crisis_result["level"],
            crisis_result["confidence"],
        )
        persona_messages.append(("system", CLINICAL_GUARDRAILS))

    routing_instructions = build_routing_instructions(next_actions)
    if routing_instructions:
        persona_messages.append(("system", routing_instructions))

    # 4. Ejecución
    try:
        from src.core.engine import get_analytical_llm

        analytical_llm = get_analytical_llm()

        from langchain_core.messages import SystemMessage

        system_messages = [SystemMessage(content=msg[1]) for msg in persona_messages]

        config = create_observable_config(call_type="cbt_therapeutic_response")
        conversational_prompt = ChatPromptTemplate.from_messages(
            system_messages
            + [
                MessagesPlaceholder(variable_name="messages"),
                ("user", "{user_message}"),
            ]
        )

        chain = conversational_prompt | analytical_llm

        # DIAGNÓSTICO TEMPORAL: medir tamaño exacto de cada componente del prompt
        sys_chars = sum(len(m.content) for m in system_messages)
        conv_chars = sum(len(m.content) for m in messages if hasattr(m, "content"))
        knowledge_chars = len(knowledge_context)
        facts_chars = len(structured_knowledge)
        persona_chars = len(build_enriched_profile_context(profile))
        total_chars = (
            sys_chars
            + conv_chars
            + len(user_message)
            + knowledge_chars
            + facts_chars
            + persona_chars
        )
        # Sub-desglose del system prompt
        sub_sizes = [len(m.content) for m in system_messages]
        logger.info(
            "[CBT-PROMPT-SIZE] total=%d sys=%d conv=%d facts=%d rag=%d "
            "profile=%d user=%d sub_sys=%s",
            total_chars,
            sys_chars,
            conv_chars,
            facts_chars,
            knowledge_chars,
            persona_chars,
            len(user_message),
            sub_sizes,
        )
        logger.info(
            "[CBT-PROMPT-SIZE] total=%d sys=%d conv=%d facts=%d rag=%d "
            "profile=%d user=%d",
            total_chars,
            sys_chars,
            conv_chars,
            facts_chars,
            knowledge_chars,
            persona_chars,
            len(user_message),
        )

        response = await chain.ainvoke(
            {"user_message": user_message, "messages": messages},
            config=cast(RunnableConfig, config),
        )
        return str(response.content).strip()

    except Exception as e:
        logger.error(f"Error en CBT tool: {e}")
        return (
            "Siento que hay mucha información de golpe y me cuesta procesarla. "
            "¿Podemos ir más despacio? Cuéntame, ¿qué es lo que más te preocupa hoy?"
        )


# Exportar para SkillLoader
SKILL_TOOL = cbt_therapeutic_guidance_tool
