# src/agents/specialists/chat_agent.py
"""
Enhanced ChatAgent with intelligent delegation and optimized performance.

Architecture restored: Intelligent delegation system (ADR-0006) with performance
optimizations from ADR-0009. Maintains <2s response time while preserving
advanced conversational capabilities.

Key features restored:
- Intelligent delegation analysis with fast LLM classification
- Integration with MasterOrchestrator for complex tasks
- Advanced conversation translation and context management
- Optimized threshold-based routing (simple vs complex messages)
"""

import base64
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph

# Import Google API exceptions with fallback
try:
    from google.api_core import exceptions as google_exceptions

    # Use generic alias to avoid mypy confusion if specific class differs inside lib versions
    ResourceExhaustedError = google_exceptions.ResourceExhausted
    GoogleAPICallError = google_exceptions.GoogleAPICallError
except ImportError:
    # Fallback para entornos donde google.api_core no está disponible
    class ResourceExhaustedError(Exception):  # type: ignore
        """Fallback ResourceExhausted exception"""

        pass

    class GoogleAPICallError(Exception):  # type: ignore
        """Fallback GoogleAPICallError exception"""

        pass


# ✅ ARCHITECTURE FIX: Use src.core.engine instead of hardcoded LLM
# ✅ FUNCTIONALITY RESTORATION: Re-import MasterOrchestrator for delegation
from src.agents.orchestrator.factory import master_orchestrator
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.profile_manager import user_profile_manager
from src.core.prompts.loader import load_text_prompt
from src.core.registry import specialist_registry
from src.core.schemas import (
    CanonicalEventV1,
    GraphStateV2,
    InternalDelegationResponse,
)
from src.memory.long_term_memory import long_term_memory
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)

# ============================================================================
# PERFORMANCE-OPTIMIZED DELEGATION ANALYSIS
# ============================================================================

DELEGATION_ANALYSIS_TEMPLATE = """Analiza si el mensaje requiere un especialista técnico (archivos, datos, planes complejos).
Historial: {conversation_history}
Responde SOLO: "DELEGAR" o "DIRECTO".
Mensaje: {user_message}"""

TRANSLATION_TEMPLATE = """Eres MAGI, un mentor estoico y práctico.
Tu tarea es traducir la respuesta técnica de un especialista a un lenguaje natural, empático y conversacional para el usuario.

CONTEXTO:
- Fecha actual: {current_date}
- Historial reciente: {conversation_history}
- Mensaje original del usuario: {original_user_message}

RESPUESTA TÉCNICA DEL ESPECIALISTA:
- Estado: {status}
- Resumen: {summary}
- Sugerencias: {suggestions}

INSTRUCCIONES:
1. NO menciones que eres una IA o que estás traduciendo una respuesta.
2. Mantén un tono estoico, directo pero útil.
3. Integra las sugerencias de forma natural en la conversación.
4. Si hay un error, explícalo de forma sencilla sin tecnicismos.
5. Responde directamente al usuario."""


# ✅ FUNCIONALIDAD RESTAURADA: Carga dinámica del prompt de personalidad (ADR-0008)
def _load_persona_prompt() -> str:
    """Carga el prompt maestro de personalidad desde el archivo."""
    content = load_text_prompt("cbt_therapeutic_response.txt")
    if content:
        return content

    # Fallback ultra simple para no fallar
    return """Eres un asistente útil. Usuario: {user_name}. Mensaje: {user_message}."""


# (CONVERSATIONAL_RESPONSE_TEMPLATE ELIMINADO - "LOBOTOMÍA INVERSA" COMPLETADA)


@tool
async def conversational_chat_tool(
    user_message: str, conversation_history: str = ""
) -> str:
    """
    ✅ FUNCTIONALITY RESTORED: Intelligent delegation tool with performance optimization.

    Advanced ChatAgent capabilities restored:
    - Fast delegation analysis (<200ms LLM call)
    - Smart routing: direct response vs specialist delegation
    - Advanced conversational context management
    - Integration with MasterOrchestrator for complex tasks
    """
    logger.info(f"Enhanced ChatAgent Tool procesando: '{user_message[:50]}...'")

    # ✅ OPTIMIZATION + FUNCTIONALITY: Fast delegation analysis
    requires_delegation = await _optimized_delegation_analysis(
        user_message, conversation_history
    )

    if not requires_delegation:
        # ✅ PERFORMANCE: Direct conversational response (<1s)
        return await _enhanced_conversational_response(
            user_message, conversation_history
        )
    else:
        # ✅ RESTORATION: Intelligent delegation with translation (<3s vs 36+s previous)
        return await _optimized_delegate_and_translate(
            user_message, conversation_history
        )


# ============================================================================
# PERFORMANCE-OPTIMIZED DELEGATION ANALYSIS FUNCTIONS
# ============================================================================


async def _optimized_delegation_analysis(
    user_message: str, conversation_history: str
) -> bool:
    """
    ✅ RESTORATION + OPTIMIZATION: Fast delegation analysis with <200ms target.

    Determines if message requires delegation to specialists using optimized
    LLM prompt designed for rapid binary classification.

    Performance target: <200ms (vs previous slower analysis)
    """
    # ✅ OPTIMIZATION: Limit conversation history for faster processing
    recent_history = _get_recent_history_summary(conversation_history, max_length=200)

    delegation_prompt = ChatPromptTemplate.from_template(DELEGATION_ANALYSIS_TEMPLATE)

    try:
        # ✅ ARCHITECTURE: Use src.core.engine instead of hardcoded LLM with observability
        config = create_observable_config(call_type="delegation_analysis")
        chain = delegation_prompt | llm
        response = await chain.ainvoke(
            {
                "user_message": user_message,
                "conversation_history": recent_history,
            },
            config=cast(RunnableConfig, config),
        )

        decision = str(response.content).strip().upper()
        should_delegate = decision == "DELEGAR"

        logger.info(
            f"Delegation analysis: '{user_message[:30]}...' → {decision} ({should_delegate})"
        )
        return should_delegate

    except Exception as e:
        logger.error(f"Error en análisis de delegación optimizado: {e}")
        # ✅ FALLBACK: Conservative approach - prefer direct response for performance
        return False


async def _get_knowledge_context(user_message: str, chat_id: str) -> str:
    """Obtiene contexto usando Smart RAG basado en el perfil."""
    await user_profile_manager.load_profile()
    active_tags = user_profile_manager.get_active_tags()
    return await file_search_tool.query_files(user_message, chat_id, tags=active_tags)


async def _enhanced_conversational_response(
    user_message: str,
    conversation_history: str,
    chat_id: str = "default_user",
    intent_signal: str = "",
    image_path: str | None = None,
    user_name: str = "Usuario",
) -> str:
    """
    ✅ RESTORATION: Advanced conversational response with memory and context awareness.
    """
    # 1. Recuperar Perfil y Estilo
    await user_profile_manager.load_profile()
    style = user_profile_manager.get_style()

    # 2. Smart RAG
    try:
        knowledge_context = await _get_knowledge_context(user_message, chat_id)
    except Exception as e:
        logger.error(f"Error recuperando contexto de conocimiento: {e}")
        knowledge_context = ""

    # 3. Preparar Prompt
    # 4. Long-Term Memory
    memory_data = await long_term_memory.get_summary(chat_id)
    history_summary = memory_data.get("summary", "Perfil activo.")
    struggles_summary = memory_data.get("struggles", "No especificado")

    # --- TIME-LOCK PROTOCOL (SIMPLIFICADO) ---
    current_date_str = datetime.now().strftime(
        "%A, %d de %B"
    )  # Solo fecha, sin año ni hora para reducir ansiedad

    # Contexto profundo del perfil v0.3.2
    ranking_context = user_profile_manager.get_context_for_prompt()

    # Cargar el template dinámicamente
    persona_template = _load_persona_prompt()
    conversational_prompt = ChatPromptTemplate.from_template(persona_template)

    prompt_input = {
        "user_name": user_name,
        "current_date": current_date_str,
        "user_message": user_message,
        "conversation_history": conversation_history,
        "knowledge_context": knowledge_context,
        "history_summary": history_summary,
        "struggles": struggles_summary,
        "intent_signal": intent_signal,
        "user_style": style,
        "user_phase": ranking_context.get("phase", "Building"),
        "key_metaphors": ranking_context.get("metaphors", "El Autobús, La Trinchera"),
    }

    try:
        config = create_observable_config(call_type="enhanced_chat_response")
        chain = conversational_prompt | llm

        # Multimodal handling
        if image_path and Path(image_path).exists():
            async with aiofiles.open(image_path, "rb") as f:
                image_data = base64.b64encode(await f.read()).decode("utf-8")
            formatted_prompt = await conversational_prompt.aformat(**prompt_input)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": formatted_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ]
            )
            response = await llm.ainvoke([message], config=cast(RunnableConfig, config))
        else:
            response = await chain.ainvoke(
                prompt_input, config=cast(RunnableConfig, config)
            )

        return str(response.content).strip()

    except ResourceExhaustedError:
        logger.error("Límite de cuota agotado en ChatAgent.")
        return "Lo siento, estoy recibiendo muchas peticiones. Por favor, espera un momento mientras recupero mi centro."
    except Exception as e:
        logger.error(f"Error en respuesta conversacional mejorada: {e}")
        return (
            "He tenido un pequeño tropiezo mental, pero sigo aquí. ¿En qué estábamos?"
        )


def _get_recent_history_summary(history: str, max_length: int = 500) -> str:
    """Optimiza el historial para el LLM."""
    if not history:
        return "No hay historial previo."
    if len(history) <= max_length:
        return history
    return "..." + history[-max_length:]


# ============================================================================
# DELEGATION & TRANSLATION LOGIC
# ============================================================================


async def _optimized_delegate_and_translate(
    user_message: str, conversation_history: str
) -> str:
    """
    ✅ RESTORATION: Intelligent delegation with natural language translation.

    Target: <3s total execution.
    """
    # 1. Delegar al MasterOrchestrator
    logger.info("ChatAgent: Delegando tarea compleja al MasterOrchestrator...")

    try:
        # Simplificamos el evento para el orquestador
        event = CanonicalEventV1(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            type="user_message",
            payload={
                "message": user_message,
                "history": conversation_history,
            },
        )

        # Invocamos al orquestador
        orchestrator_response = await master_orchestrator.process_event(event)

        # 2. Traducir la respuesta técnica a algo conversacional
        return await _translate_specialist_response(
            orchestrator_response, user_message, conversation_history
        )

    except Exception as e:
        logger.error(f"Error en delegación/traducción: {e}")
        return "He intentado coordinar una respuesta compleja pero algo ha fallado. ¿Podemos intentarlo de otra forma?"


async def _translate_specialist_response(
    specialist_response: Any, original_user_message: str, conversation_history: str
) -> str:
    """
    ✅ FUNCTIONALITY RESTORATION: Translates technical specialist responses to conversational language.

    Converts structured specialist responses into natural, user-friendly conversation
    while maintaining all important information and context.
    """
    # Handle different response types
    if isinstance(specialist_response, InternalDelegationResponse):
        status = specialist_response.status
        summary = specialist_response.summary
        suggestions = ", ".join(specialist_response.suggestions)
    elif isinstance(specialist_response, dict):
        status = specialist_response.get("status", "completado")
        summary = specialist_response.get("summary", str(specialist_response))
        suggestions = ", ".join(specialist_response.get("suggestions", []))
    else:
        # Fallback for simple responses
        return str(specialist_response)

    translation_prompt = ChatPromptTemplate.from_template(TRANSLATION_TEMPLATE)

    try:
        # ✅ ARCHITECTURE: Use src.core.engine with observability
        config = create_observable_config(call_type="response_translation")
        chain = translation_prompt | llm

        # ✅ TIME AWARENESS: Inyectar fecha y hora actual
        current_date = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")

        response = await chain.ainvoke(
            {
                "conversation_history": conversation_history,
                "original_user_message": original_user_message,
                "status": status,
                "summary": summary,
                "suggestions": suggestions,
                "current_date": current_date,
            },
            config=cast(RunnableConfig, config),
        )

        return str(response.content).strip()

    except Exception as e:
        logger.error(f"Error traduciendo respuesta de especialista: {e}")
        return f"El especialista ha completado la tarea (Estado: {status}). Resumen: {summary}"


# ============================================================================
# SPECIALIST INTERFACE IMPLEMENTATION
# ============================================================================


class ChatSpecialist(SpecialistInterface):
    """
    Especialista conversacional y orquestador de primer nivel.
    Implementa SpecialistInterface para integración en el registry.
    """

    def __init__(self):
        self._name: str = "chat_agent"
        # Grafo simplificado: solo un nodo que llama a la herramienta
        self._graph: Any = self._build_graph()
        self._tool: BaseTool = conversational_chat_tool

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Any:
        return self._graph

    @property
    def tool(self) -> BaseTool:
        return self._tool

    def get_capabilities(self) -> list[str]:
        """El ChatAgent es capaz de manejar conversación general y delegación."""
        return ["chat", "delegation", "conversational"]

    def _build_graph(self) -> Any:
        """Construye un grafo mínimo para el especialista."""
        workflow = StateGraph(GraphStateV2)
        workflow.add_node("chat", self._chat_node)
        workflow.set_entry_point("chat")
        # El orquestador manejará el flujo después de este nodo
        return workflow.compile()

    async def _chat_node(self, state: GraphStateV2) -> dict[str, Any]:
        """Nodo que procesa el chat usando la herramienta conversacional."""
        payload = state.get("payload", {})
        user_message = payload.get("message", "")
        history = payload.get("history", "")
        chat_id = state.get("session_id", "default_user")

        # Inyectar señales de intención si existen
        intent_type = payload.get("intent", "conversational")
        file_presence = payload.get("file_presence", False)
        file_presence_info = (
            "(Usuario ha enviado archivos)" if file_presence else "(Sin archivos)"
        )

        # Pasamos la intención detectada al generador de respuesta
        intent_signal_text = f"Intención detectada: {intent_type}. {file_presence_info}"

        # Extraer ruta de imagen si existe en el payload
        image_path = state.get("payload", {}).get("image_file_path")

        # Extraer nombre usuario si existe
        # Re-importing inside method for safety if needed, but it's at module level
        user_name = payload.get("user_name", "Usuario")

        response_text = await _enhanced_conversational_response(
            user_message,
            history,
            chat_id=chat_id,
            intent_signal=intent_signal_text,
            image_path=image_path,
            user_name=user_name,
        )

        # Actualizar el payload con la respuesta
        payload["response"] = response_text
        payload["last_specialist"] = self.name
        payload["next_action"] = "respond_to_user"

        return {"payload": payload}


# Registrar el especialista
specialist_registry.register(ChatSpecialist())
