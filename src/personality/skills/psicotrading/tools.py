"""Tool de psicotrading: coaching psicológico para traders."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from src.personality.prompt_builder import system_prompt_builder

logger = logging.getLogger(__name__)


@tool
async def psicotrading_guidance_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    routing_metadata: dict[str, Any] | None = None,
) -> str:
    """Coaching psicológico para traders (sesgos, gestión emocional)."""
    # Importar aquí para evitar circular imports
    from src.core.engine import llm
    from src.core.message_utils import dict_to_langchain_messages
    from src.core.profile_manager import user_profile_manager

    try:
        profile = await user_profile_manager.load_profile(chat_id)

        # Construir el prompt dinámico usando el Soul Stack
        persona_template = await system_prompt_builder.build(
            profile=profile,
            skill_name="psicotrading",
            runtime_context={},
            recent_user_messages=[user_message],
        )

        conversational_prompt = ChatPromptTemplate.from_messages([
            ("system", persona_template),
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{user_message}"),
        ])

        # Formatear historial
        messages = dict_to_langchain_messages(conversation_history or [], limit=20)

        chain = conversational_prompt | llm
        response = await chain.ainvoke({
            "user_message": user_message,
            "messages": messages,
        })

        return str(response.content).strip()

    except Exception:
        logger.exception("Error en psicotrading tool")
        return (
            "Detecto algo de ruido en tu frecuencia operativa. "
            "¿Podemos analizar qué estás sintiendo respecto a esta operación?"
        )


# Exportar para SkillLoader
SKILL_TOOL = psicotrading_guidance_tool
