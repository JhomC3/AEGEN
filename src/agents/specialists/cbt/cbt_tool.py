import logging
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt
from src.core.dependencies import get_vector_memory_manager
from src.core.engine import create_observable_config, llm
from src.core.message_utils import dict_to_langchain_messages
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

    # 1. Cargar perfil (Diskless/Multi-user)
    profile = await user_profile_manager.load_profile(chat_id)

    # 2. Recuperar Memoria de Largo Plazo (Resumen + Hechos Estructurados)
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Sin historial previo.")

    knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
    structured_knowledge = format_knowledge_for_prompt(knowledge_data)

    # 3. Smart RAG (Conocimiento TCC)
    try:
        manager = get_vector_memory_manager()
        # Buscar en conocimiento global (TCC)
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=3, namespace="global"
        )

        # Buscar en conocimiento del usuario
        user_results = await manager.retrieve_context(
            user_id=chat_id, query=user_message, limit=2, namespace="user"
        )

        all_results = global_results + user_results

        # Transparencia RAG
        logger.info(
            f"[CBT-RAG] Injecting context: {len(global_results)} global + "
            f"{len(user_results)} user fragments for chat={chat_id}"
        )

        knowledge_context = (
            "\n\n".join([f"- {r['content']}" for r in all_results])
            if all_results
            else "No hay contexto documental disponible."
        )

    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        knowledge_context = "No hay contexto documental disponible."

    # 4. Construir instrucciones adicionales basadas en next_actions
    routing_instructions = build_routing_instructions(next_actions)

    persona_template = await system_prompt_builder.build(
        chat_id=chat_id,
        profile=profile,
        skill_name="tcc",
        runtime_context={
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
    )

    # Inyectar perfil enriquecido
    enriched_context = build_enriched_profile_context(profile)
    if enriched_context:
        persona_template += f"\n\n{enriched_context}"

    # Inyectar guardrails clínicos
    persona_template += CLINICAL_GUARDRAILS

    # Inyectar instrucciones de routing al final del system prompt
    if routing_instructions:
        persona_template += routing_instructions

    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        adaptation = user_profile_manager.get_personality_adaptation(profile)
        history_limit = adaptation.get("history_limit", 20)
        messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

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
        return "Respiro hondo. Mantén la calma, el mercado es solo ruido. Cuéntame más sobre lo que sientes."
