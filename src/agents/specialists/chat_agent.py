# src/agents/specialists/chat_agent.py
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.agents.orchestrator import master_orchestrator
from src.core.engine import llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import CanonicalEventV1, GraphStateV2, InternalDelegationResponse

logger = logging.getLogger(__name__)


@tool
async def conversational_chat_tool(
    user_message: str, conversation_history: str = ""
) -> str:
    """
    Herramienta principal del ChatAgent con capacidad de delegación inteligente.

    Nueva arquitectura ADR-0006:
    1. Analiza si el mensaje requiere delegación a especialistas
    2. Si no requiere delegación: responde directamente
    3. Si requiere delegación: delega y traduce la respuesta a lenguaje natural
    """
    logger.info(f"ChatAgent procesando: '{user_message[:50]}...'")

    # Paso 1: Analizar si requiere delegación
    requires_delegation = await _analyze_delegation_need(
        user_message, conversation_history
    )

    if not requires_delegation:
        # Respuesta conversacional directa
        return await _direct_conversational_response(user_message, conversation_history)
    else:
        # Delegación a especialista + traducción
        return await _delegate_and_translate(user_message, conversation_history)


async def _analyze_delegation_need(
    user_message: str, conversation_history: str
) -> bool:
    """
    Analiza si el mensaje del usuario requiere delegación a un especialista.

    Criterios para delegación:
    - Tareas complejas (planificación, análisis, transcripción)
    - Procesamiento de archivos
    - Solicitudes técnicas específicas

    Returns:
        bool: True si requiere delegación, False para conversación directa
    """
    delegation_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Eres un clasificador de intenciones que determina si un mensaje del usuario requiere delegación a especialistas o puede manejarse con conversación directa.

DELEGAR a especialistas si el mensaje incluye:
- Planificación de tareas complejas
- Análisis técnico o de datos
- Procesamiento de archivos (audio, documentos)
- Solicitudes que requieren herramientas específicas

CONVERSACIÓN DIRECTA para:
- Saludos, agradecimientos, despedidas
- Preguntas simples sobre el sistema
- Conversación casual
- Clarificaciones sencillas

Historial conversacional:
{conversation_history}

Responde SOLO con: "DELEGAR" o "DIRECTO" """,
        ),
        ("human", "{user_message}"),
    ])

    try:
        chain = delegation_prompt | llm
        response = await chain.ainvoke({
            "user_message": user_message,
            "conversation_history": conversation_history,
        })
        decision = str(response.content).strip().upper()
        return decision == "DELEGAR"
    except Exception as e:
        logger.error(f"Error en análisis de delegación: {e}")
        # En caso de error, usar conversación directa como fallback
        return False


async def _direct_conversational_response(
    user_message: str, conversation_history: str
) -> str:
    """
    Genera respuesta conversacional directa sin delegación.
    """
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Eres AEGEN, un asistente de IA conversacional, inteligente y amigable.

Tu personalidad:
- Eres natural, empático y profesional
- Respondes de manera concisa pero completa
- Mantienes el contexto de la conversación
- Eres proactivo para ayudar al usuario

Contexto conversacional previo:
{conversation_history}

Responde de manera natural y conversacional.""",
        ),
        ("human", "{user_message}"),
    ])

    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "user_message": user_message,
            "conversation_history": conversation_history,
        })
        return str(response.content)
    except Exception as e:
        logger.error(f"Error en respuesta directa: {e}", exc_info=True)
        return "Disculpa, tuve un problema técnico. ¿Podrías intentar de nuevo?"


async def _delegate_and_translate(user_message: str, conversation_history: str) -> str:
    """
    Delega la tarea a un especialista vía MasterOrchestrator y traduce la respuesta.
    """
    logger.info(f"Delegando tarea compleja: '{user_message[:50]}...'")

    try:
        # Crear evento canónico para el MasterOrchestrator
        event = CanonicalEventV1(
            event_id="chat_delegation",
            event_type="text",
            content=user_message,
            user_id="system",
            timestamp=None
        )
        
        # Crear estado inicial para MasterOrchestrator
        initial_state = GraphStateV2(
            event=event,
            payload={"user_message": user_message},
            conversation_history=[]
        )
        
        # Llamada real al MasterOrchestrator
        final_state = await master_orchestrator.run(initial_state)
        
        # Extraer respuesta del payload
        response = final_state.get("payload", {}).get("response", "")
        error_message = final_state.get("error_message")
        
        if error_message:
            logger.error(f"Error en delegación: {error_message}")
            return f"Disculpa, hubo un problema procesando tu solicitud: {error_message}"
        
        if not response:
            logger.warning("No se recibió respuesta del especialista")
            return "He procesado tu solicitud pero no pude generar una respuesta específica."
            
        # La respuesta del especialista ya está en formato conversacional
        return str(response)
        
    except Exception as e:
        error_msg = f"Error en delegación al MasterOrchestrator: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return "Disculpa, tuve un problema técnico al procesar tu solicitud."


async def _translate_specialist_response(
    specialist_response: InternalDelegationResponse,
    original_user_message: str,
    conversation_history: str,
) -> str:
    """
    Traduce la respuesta técnica del especialista a lenguaje conversacional natural.
    """
    translation_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Eres AEGEN, un asistente conversacional que traduce respuestas técnicas a lenguaje natural.

Tu trabajo es tomar la respuesta de un especialista interno y convertirla en una respuesta conversacional amigable para el usuario.

Directrices:
- Usa un tono natural y conversacional
- Evita jerga técnica
- Mantén la información importante del especialista
- Sé empático y útil

Contexto conversacional:
{conversation_history}

Mensaje original del usuario: {original_user_message}

Respuesta del especialista:
Status: {status}
Resumen: {summary}
Sugerencias: {suggestions}
""",
        ),
        (
            "human",
            "Traduce la respuesta del especialista a lenguaje conversacional natural",
        ),
    ])

    try:
        chain = translation_prompt | llm
        response = await chain.ainvoke({
            "conversation_history": conversation_history,
            "original_user_message": original_user_message,
            "status": specialist_response.status,
            "summary": specialist_response.summary,
            "suggestions": ", ".join(specialist_response.suggestions),
        })
        return str(response.content)
    except Exception as e:
        logger.error(f"Error en traducción de respuesta: {e}")
        # Fallback a la respuesta directa del especialista
        return specialist_response.summary


class ChatSpecialist(SpecialistInterface):
    """
    Agente especializado en conversación general.
    """

    def __init__(self):
        self._name = "chat_specialist"
        self._graph = self._build_graph()
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
        """Este agente maneja eventos de texto plano."""
        return ["text"]

    def _build_graph(self) -> Any:
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("chat", self._chat_node)
        graph_builder.set_entry_point("chat")
        graph_builder.add_edge("chat", END)
        return graph_builder.compile()

    async def _chat_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Nodo principal del agente de chat. Valida el estado y ejecuta la herramienta.
        """
        try:
            event_obj = state["event"]
        except KeyError:
            return {"error_message": "El evento no se encontró en el estado."}

        user_message = event_obj.content or ""

        # Build conversation history string from state
        conversation_history = state.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_parts.append(f"{role.capitalize()}: {content}")
            history_text = "\n".join(history_parts)

        result = await self.tool.ainvoke({
            "user_message": user_message,
            "conversation_history": history_text,
        })

        # Update conversation history like PlannerAgent does
        updated_history = list(conversation_history)
        if user_message:
            updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": str(result)})

        current_payload = state.get("payload", {})
        return {
            "payload": {**current_payload, "response": result},
            "conversation_history": updated_history,
        }


# ChatAgent activado para nueva arquitectura conversacional (ADR-0006)
specialist_registry.register(ChatSpecialist())
