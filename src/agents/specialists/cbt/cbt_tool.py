import json
import logging
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt
from src.core.dependencies import get_vector_memory_manager
from src.core.engine import create_observable_config, llm_core
from src.core.message_utils import (
    dict_to_langchain_messages,
)
from src.core.profile_manager import user_profile_manager
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory

logger = logging.getLogger(__name__)

class TherapeuticPlan(BaseModel):
    insight: str = Field(
        description="Análisis del usuario, identificando distorsiones"
    )
    action_to_propose: str = Field(
        description="Instrucción estricta de lo que MAGI debe decir "
        "(ej. 'Proponle cambiar el tema')"
    )

async def _get_cbt_rag_context(chat_id: str, user_message: str) -> str:
    """Recupera contexto TCC relevante usando Smart RAG."""
    try:
        manager = get_vector_memory_manager()
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=3, namespace="global"
        )
        user_results = await manager.retrieve_context(
            user_id=chat_id, query=user_message, limit=2, namespace="user"
        )

        all_results = global_results + user_results

        if all_results:
            formatted_results = []
            for r in all_results:
                source = r.get("metadata", {}).get("filename", "Memoria de Usuario")
                formatted_results.append(f"- [Fuente: {source}] {r['content']}")
            return "\n\n".join(formatted_results)
        return "No hay contexto documental disponible."
    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        return "No hay contexto documental disponible."

async def _get_cbt_memories(chat_id: str) -> tuple[str, str]:
    """Recupera resumen de memoria y hechos para CBT."""
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.summary
    knowledge_data = await knowledge_base_manager.load_knowledge(chat_id)
    structured_knowledge = format_knowledge_for_prompt(knowledge_data)
    return history_summary, structured_knowledge

@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    chat_id: str,
    conversation_history: list[dict[str, Any]] | None = None,
    routing_metadata: dict[str, Any] | None = None,
    session_context: dict[str, Any] | None = None,
) -> str:
    """
    Estratega Clínico Silencioso (Think-then-Speak pattern).
    Retorna un JSON plan que será pasado a MAGI (chat_specialist) para comunicarlo.
    """
    if conversation_history is None:
        conversation_history = []

    routing_metadata = routing_metadata or {}
    session_context = session_context or {}

    profile = await user_profile_manager.load_profile(chat_id)
    knowledge_context = await _get_cbt_rag_context(chat_id, user_message)
    history_summary, structured_knowledge = await _get_cbt_memories(chat_id)

    adaptation = user_profile_manager.get_personality_adaptation(profile)
    history_limit = adaptation.get("history_limit", 20)
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres el Estratega Psicológico Interno de AEGEN. No hablas con el usuario.\n"
         "Tu trabajo es analizar la conversación y crear un plan para MAGI.\n\n"
         f"Memoria: {history_summary}\n\n"
         f"Teoría (RAG): {knowledge_context}\n\n"
         "INSTRUCCIÓN DE PLANIFICACIÓN:\n"
         "1. Identifica el bloqueo del usuario.\n"
         "2. Diseña una instrucción de acción para que MAGI se la diga al usuario.\n"
         "3. Si el usuario está muy deprimido, la acción debe ser MUY pequeña.\n"
         "4. Responde estrictamente usando la función JSON."
        ),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "{user_message}"),
    ])

    try:
        config = create_observable_config(call_type="cbt_therapeutic_plan")
        chain = prompt | llm_core.with_structured_output(TherapeuticPlan)
        plan: TherapeuticPlan = await chain.ainvoke(
            {"user_message": user_message, "messages": messages},
            config=cast(RunnableConfig, config),
        )
        return json.dumps(plan.model_dump(), ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error en CBT tool: {e}")
        return json.dumps({
            "insight": "Error en el análisis",
            "action_to_propose": "Dile al usuario que respire profundo."
        })
