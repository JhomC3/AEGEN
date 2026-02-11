# src/agents/orchestrator/routing/routing_utils.py
"""
Utilidades para manipulación de estado en routing decisions.

Funciones puras para actualizar GraphStateV2 evitando duplicación
y centralizando lógica de gestión de estado.
"""

import logging
import re
from typing import Any

from src.core.routing_models import RoutingDecision
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Constantes
CHAT_SPECIALIST_NODE = "chat_specialist"


def route_to_chat(state: GraphStateV2) -> str:
    """
    Routing fallback a ChatBot specialist.

    Args:
        state: Estado del grafo a modificar

    Returns:
        str: Nombre del nodo ChatBot specialist
    """
    if "payload" not in state:
        state["payload"] = {}

    state["payload"]["next_node"] = CHAT_SPECIALIST_NODE
    logger.debug("Routing fallback a ChatBot")
    return CHAT_SPECIALIST_NODE


def is_conversational_only(text: str) -> bool:
    """
    Detecta si un mensaje es puramente conversacional (saludo/despedida/gratitud)
    para evitar costo de LLM Router.
    """
    # Si detectamos un comando explícito, NO es conversacional solamente,
    # debe pasar por el router o ser procesado.
    if detect_explicit_command(text):
        return False

    text = text.strip().lower()

    # Patrones de saludos simples y cortesía
    patterns = [
        r"^(hola|buenos\s*dias|buenas\s*tardes|buenas\s*noches|hey|hi|hello)[!.]*$",
        r"^(gracias|muchas\s*gracias|ok|vale|listo|entendido|grx|thx)[!.]*$",
        r"^(adios|chau|hasta\s*luego|nos\s*vemos|bye)[!.]*$",
        r"^(como\s*estas|que\s*tal|todo\s*bien)[?!.]*$",
    ]

    # Verificar Regex para saludos explícitos
    if any(re.match(p, text) for p in patterns):
        return True

    return False


def detect_explicit_command(text: str) -> str | None:
    """
    Detecta si el usuario está usando un comando explícito para activar un especialista.
    Ejemplos: /tcc, /terapeuta, /debug, /coding
    """
    text = text.strip().lower()

    commands = {
        "cbt_specialist": [r"^/tcc", r"^/terapeuta", r"^/psicologo"],
        "chat_specialist": [r"^/chat", r"^/magi"],
        # Futuros especialistas
        "coding_specialist": [r"^/coding", r"^/code", r"^/programar"],
    }

    for specialist, patterns in commands.items():
        if any(re.search(p, text) for p in patterns):
            return specialist

    return None


def update_state_with_decision(state: GraphStateV2, decision: RoutingDecision) -> None:
    """
    Actualiza estado del grafo con información de routing decision.

    Args:
        state: Estado del grafo a modificar
        decision: Decisión de routing con metadata completa
    """
    if "payload" not in state:
        state["payload"] = {}

    payload = state["payload"]
    payload.update({
        "next_node": decision.target_specialist,
        "routing_decision": decision.model_dump(),
        "intent": decision.intent.value,
        "entities": [entity.model_dump() for entity in decision.entities],
        "confidence": decision.confidence,
        "requires_tools": decision.requires_tools,
    })

    logger.info(
        f"Estado actualizado: {decision.intent} → {decision.target_specialist} "
        f"(confianza: {decision.confidence:.2f})"
    )


def extract_context_from_state(state: GraphStateV2) -> dict[str, Any]:
    """
    Extrae contexto conversacional del estado para análisis.

    Args:
        state: Estado del grafo con historial y metadata

    Returns:
        Dict: Contexto estructurado para análisis LLM
    """
    event = state["event"]
    history = state.get("conversation_history", [])

    # Explicitly type context as dict[str, Any] to avoid incorrect type inference
    context: dict[str, Any] = {}

    # Información del usuario
    if hasattr(event, "user_id"):
        context["user_id"] = event.user_id

    # Historial conversacional
    if history:
        context["history_length"] = len(history)
        # Últimos 5 mensajes para contexto inmediato y continuidad
        recent_messages = history[-5:] if len(history) >= 5 else history
        context["recent_interactions"] = len(recent_messages)

        # Extraer contenido formateado para el LLM
        formatted_history = []
        for msg in recent_messages:
            # Identificar rol (V2ChatMessage usa 'role')
            role = "Asistente" if msg.get("role") == "assistant" else "Usuario"
            content = msg.get("content", "")
            if content:
                formatted_history.append(f"{role}: {content}")

        context["recent_messages_content"] = formatted_history
    else:
        context["history_length"] = 0
        context["recent_interactions"] = 0
        context["recent_messages_content"] = []

    # Información de ruteo previo (desde la sesión persistente)
    payload = state.get("payload", {})

    # Intent previo
    prev_intent = payload.get("last_intent") or payload.get("intent")
    if prev_intent:
        context["previous_intent"] = prev_intent

    # Especialista previo
    prev_specialist = payload.get("last_specialist") or payload.get("next_node")
    if prev_specialist:
        context["previous_specialist"] = prev_specialist

    # Inyectar contexto de sesión si existe
    if payload.get("session_context"):
        context["session_context"] = payload["session_context"]

    return context


def format_context_for_llm(context: dict[str, Any]) -> str:
    """
    Formatea contexto para inclusión en prompt LLM.

    Args:
        context: Diccionario con información contextual

    Returns:
        str: Contexto formateado para prompt
    """
    if not context:
        return "Sin contexto previo"

    parts = []

    if context.get("user_id"):
        parts.append(f"Usuario: {context['user_id']}")

    if context.get("history_length", 0) > 0:
        parts.append(f"Historial: {context['history_length']} mensajes")

    if context.get("previous_intent"):
        parts.append(f"Intent anterior: {context['previous_intent']}")

    if context.get("previous_specialist"):
        parts.append(f"Especialista previo: {context['previous_specialist']}")

    # A.2: Inyectar contenido real de los últimos mensajes para continuidad narrativa
    if context.get("recent_messages_content"):
        history_str = "\n".join(context["recent_messages_content"])
        parts.append(f"\nÚLTIMOS MENSAJES (Diálogo):\n{history_str}")

    return " | ".join(parts) if parts else "Sesión nueva"
