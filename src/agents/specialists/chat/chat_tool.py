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


@tool
async def conversational_chat_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    image_path: str | None = None,
    routing_metadata: dict[str, Any] | None = None,
) -> str:
    """
    Genera una respuesta empática y contextual usando el perfil del usuario.
    """
    if conversation_history is None:
        conversation_history = []

    routing_metadata = routing_metadata or {}
    next_actions = routing_metadata.get("next_actions", [])

    # 1. Cargar perfil (Diskless/Multi-user)
    profile = await user_profile_manager.load_profile(chat_id)

    # 2. Smart RAG
    try:
        manager = get_vector_memory_manager()
        # Buscar en conocimiento global
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=2, namespace="global"
        )

        # Buscar en conocimiento del usuario
        user_results = await manager.retrieve_context(
            user_id=chat_id, query=user_message, limit=2, namespace="user"
        )

        all_results = global_results + user_results

        if all_results:
            knowledge_context = "\n\n".join([f"- {r['content']}" for r in all_results])
        else:
            knowledge_context = ""

    except Exception as e:
        logger.warning(f"Error en RAG Chat: {e}")
        knowledge_context = ""

    # Memoria de Largo Plazo (Resumen + Hechos)
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Perfil activo.")

    knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
    structured_knowledge = format_knowledge_for_prompt(knowledge_data)

    # Instrucciones de monitoreo emocional (Low Confidence Vulnerability)
    routing_instructions = ""
    if "monitor_emotional_cues" in next_actions:
        routing_instructions = (
            "\n\nAVISO DE ENRUTAMIENTO: Se han detectado señales sutiles de vulnerabilidad. "
            "Mantén un tono empático y valida sus sentimientos si parece necesario, "
            "pero sin forzar una conversación terapéutica profunda.\n"
        )

    # Configurar límite de historial desde el perfil
    adaptation = user_profile_manager.get_personality_adaptation(profile)
    history_limit = adaptation.get("history_limit", 20)

    # Convertir historial a mensajes de LangChain
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

    # Extraer mensajes recientes del usuario para análisis de estilo (Espejo)
    recent_user_msgs = extract_recent_user_messages(messages)

    persona_template = await system_prompt_builder.build(
        chat_id=chat_id,
        profile=profile,
        skill_name="chat",
        runtime_context={
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
        recent_user_messages=recent_user_msgs,
    )

    if routing_instructions:
        persona_template += routing_instructions

    # Usamos un template más simple ya que el builder construye casi todo
    conversational_prompt = ChatPromptTemplate.from_messages([
        ("system", persona_template),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "{user_message}"),
    ])

    prompt_input = {
        "user_message": user_message,
        "messages": messages,
    }

    try:
        config = create_observable_config(call_type="chat_response")

        if image_path and Path(image_path).exists():
            return await process_image_input(
                image_path,
                prompt_input,
                conversational_prompt,
                cast(RunnableConfig, config),
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
