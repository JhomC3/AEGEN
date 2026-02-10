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
from src.memory.vector_memory_manager import VectorMemoryManager
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
async def query_user_history(chat_id: str, query: str) -> str:
    """
    5.2: Consulta el historial profundo del usuario para recuperar detalles del pasado.
    Útil para recordar metas, valores o eventos conversados hace mucho tiempo.
    """
    manager = VectorMemoryManager()
    results = await manager.retrieve_context(user_id=chat_id, query=query, limit=5)

    if not results:
        return "No se encontraron detalles relevantes en el historial."

    context_parts = [f"[{r['created_at']}] {r['content']}" for r in results]
    return "\n\n".join(context_parts)


def _build_routing_instructions(next_actions: list[str]) -> str:
    """Helper para construir instrucciones de enrutamiento sin aumentar la complejidad de la tool."""
    if not next_actions:
        return ""

    instructions = "\n\nINSTRUCCIONES DE ENRUTAMIENTO PRIORITARIAS:\n"
    mapping = {
        "depth_empathy": "- Prioriza la validación emocional profunda antes de cualquier técnica.\n",
        "clarify_emotional_state": "- El estado emocional es ambiguo. Haz una pregunta suave para clarificar cómo se siente realmente.\n",
        "active_listening": "- Usa escucha activa reflexiva. Parafrasea lo que el usuario dijo.\n",
        "gentle_probe": "- Indaga con delicadeza sobre pensamientos automáticos subyacentes.\n",
    }

    for action in next_actions:
        if action in mapping:
            instructions += mapping[action]

    return instructions


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
        manager = VectorMemoryManager()
        # Buscar en conocimiento global (TCC)
        global_results = await manager.retrieve_context(
            user_id="system", query=user_message, limit=3, namespace="global"
        )

        # Buscar en conocimiento del usuario
        user_results = await manager.retrieve_context(
            user_id=chat_id, query=user_message, limit=2, namespace="user"
        )

        all_results = global_results + user_results
        knowledge_context = (
            "\n\n".join([f"- {r['content']}" for r in all_results])
            if all_results
            else "No hay contexto documental disponible."
        )

    except Exception as e:
        logger.warning(f"Error en RAG TCC: {e}")
        knowledge_context = "No hay contexto documental disponible."

    # 4. Construir instrucciones adicionales basadas en next_actions
    routing_instructions = _build_routing_instructions(next_actions)

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
