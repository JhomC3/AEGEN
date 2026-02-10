# src/agents/specialists/chat_agent.py
"""
MAGI: El Asistente Conversacional Principal de AEGEN.
Maneja la interacción directa con el usuario, integrando memoria y perfil psicológico.
"""

import base64
import logging
from pathlib import Path
from typing import Any, cast

import aiofiles
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.agents.utils.state_utils import extract_user_content_from_state
from src.core.dependencies import get_vector_memory_manager
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.message_utils import dict_to_langchain_messages
from src.core.profile_manager import user_profile_manager
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory
from src.personality.prompt_builder import system_prompt_builder

logger = logging.getLogger(__name__)


def format_knowledge_for_prompt(knowledge: dict[str, Any]) -> str:
    """Formatea la Bóveda de Conocimiento para el prompt."""
    sections = []

    def fmt_attrs(attrs: dict) -> str:
        """Helper para formatear atributos de forma limpia."""
        if not attrs:
            return ""
        return ", ".join([f"{k}={v}" for k, v in attrs.items()])

    if knowledge.get("entities"):
        ents = "\n".join([
            f"- {e['name']} ({e['type']}): {fmt_attrs(e.get('attributes', {}))}"
            for e in knowledge["entities"]
        ])
        sections.append(f"ENTIDADES:\n{ents}")

    if knowledge.get("medical"):
        meds = "\n".join([
            f"- {m['name']} ({m['type']}): {m.get('details', '')}"
            for m in knowledge["medical"]
        ])
        sections.append(f"DATOS MÉDICOS:\n{meds}")

    if knowledge.get("relationships"):
        rels = "\n".join([
            f"- {r['person']} ({r['relation']}): {fmt_attrs(r.get('attributes', {}))}"
            for r in knowledge["relationships"]
        ])
        sections.append(f"RELACIONES:\n{rels}")

    if knowledge.get("preferences"):
        prefs = "\n".join([
            f"- {p['category']}: {p['value']}" for p in knowledge["preferences"]
        ])
        sections.append(f"PREFERENCIAS:\n{prefs}")

    return "\n\n".join(sections) if sections else "No hay hechos confirmados aún."


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

    persona_template = await system_prompt_builder.build(
        chat_id=chat_id,
        profile=profile,
        skill_name="chat",
        runtime_context={
            "history_summary": history_summary,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
    )

    if routing_instructions:
        persona_template += routing_instructions

    # Configurar límite de historial desde el perfil
    adaptation = user_profile_manager.get_personality_adaptation(profile)
    history_limit = adaptation.get("history_limit", 20)

    # Convertir historial a mensajes de LangChain
    messages = dict_to_langchain_messages(conversation_history, limit=history_limit)

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

    payload = state.get("payload", {})
    image_path = payload.get("image_file_path")
    routing_decision = payload.get("routing_decision", {})

    response_text = await conversational_chat_tool.ainvoke({
        "user_message": user_content,
        "chat_id": chat_id,
        "conversation_history": raw_history,
        "image_path": image_path,
        "routing_metadata": routing_decision,
    })

    # Actualizar historial de sesión
    updated_history = list(raw_history)
    updated_history.append({"role": "user", "content": user_content})
    updated_history.append({"role": "assistant", "content": response_text})

    state["payload"]["response"] = response_text
    state["payload"]["last_specialist"] = "chat_specialist"
    state["payload"]["next_action"] = "respond_to_user"
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
