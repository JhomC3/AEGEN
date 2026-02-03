import logging
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

from src.agents.utils.state_utils import (
    extract_user_content_from_state,
)
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.message_utils import dict_to_langchain_messages
from src.core.profile_manager import user_profile_manager
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.long_term_memory import long_term_memory
from src.personality.prompt_builder import system_prompt_builder
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


def format_knowledge_for_prompt(knowledge: dict[str, Any]) -> str:
    """Formatea la Bóveda de Conocimiento para el prompt."""
    sections = []

    if knowledge.get("entities"):
        ents = "\n".join([
            f"- {e['name']} ({e['type']}): {e.get('attributes', {})}"
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
            f"- {r['person']} ({r['relation']}): {r.get('attributes', {})}"
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
async def query_user_history(chat_id: str, query: str) -> str:
    """
    5.2: Consulta el historial profundo del usuario para recuperar detalles del pasado.
    Útil para recordar metas, valores o eventos conversados hace mucho tiempo.
    """
    return await file_search_tool.search_user_history(chat_id, query)


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
        active_tags = user_profile_manager.get_active_tags(profile)
        knowledge_context = await file_search_tool.query_files(
            user_message, chat_id, tags=active_tags, intent_type="vulnerability"
        )
    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        knowledge_context = "No hay contexto documental disponible."

    # 4. Construir instrucciones adicionales basadas en next_actions
    routing_instructions = ""
    if next_actions:
        routing_instructions = "\n\nINSTRUCCIONES DE ENRUTAMIENTO PRIORITARIAS:\n"
        if "depth_empathy" in next_actions:
            routing_instructions += "- Prioriza la validación emocional profunda antes de cualquier técnica.\n"
        if "clarify_emotional_state" in next_actions:
            routing_instructions += "- El estado emocional es ambiguo. Haz una pregunta suave para clarificar cómo se siente realmente.\n"
        if "active_listening" in next_actions:
            routing_instructions += (
                "- Usa escucha activa reflexiva. Parafrasea lo que el usuario dijo.\n"
            )
        if "gentle_probe" in next_actions:
            routing_instructions += (
                "- Indaga con delicadeza sobre pensamientos automáticos subyacentes.\n"
            )

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

    # Inyectar instrucciones de routing al final del system prompt
    if routing_instructions:
        persona_template += routing_instructions

    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")

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

        chain = conversational_prompt | llm

        prompt_input = {
            "user_message": user_message,
            "messages": messages,
        }

        response = await chain.ainvoke(
            prompt_input, config=cast(RunnableConfig, config)
        )
        return str(response.content).strip()

    except Exception as e:
        logger.error(f"Error en CBT tool: {e}")
        return "Respiro hondo. Mantén la calma, el mercado es solo ruido. Cuéntame más sobre lo que sientes."


class CBTSpecialist(SpecialistInterface):
    """
    Especialista en Terapia Cognitivo Conductual (CBT).
    """

    def __init__(self):
        self._name = "cbt_specialist"
        self._tool = cbt_therapeutic_guidance_tool
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
        return ["cbt", "psychology", "emotional_support"]

    def _build_graph(self) -> Any:
        workflow = StateGraph(GraphStateV2)
        workflow.add_node("cbt_node", self._cbt_node)
        workflow.set_entry_point("cbt_node")
        return workflow.compile()

    async def _cbt_node(self, state: GraphStateV2) -> dict[str, Any]:
        """Nodo principal CBT - Professional Clinical Psychologist"""
        logger.info("CBT Node procesando...")

        user_content = extract_user_content_from_state(state)
        if not user_content:
            return cast(dict[str, Any], state)

        chat_id = state.get("session_id", "default_user")

        # Formatear historial para el prompt (mensajes recientes)
        raw_history = state.get("conversation_history", [])

        # 2. Ejecutar Tool
        routing_decision = state.get("payload", {}).get("routing_decision", {})

        response_text = await self.tool.ainvoke({
            "user_message": user_content,
            "chat_id": chat_id,
            "conversation_history": raw_history,
            "routing_metadata": routing_decision,
        })

        # 3. Actualizar Estado
        state["payload"]["response"] = response_text
        state["payload"]["last_specialist"] = "cbt_specialist"
        state["payload"]["next_action"] = "respond_to_user"

        return cast(dict[str, Any], state)


# Registro automático
specialist_registry.register(CBTSpecialist())
