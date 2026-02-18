# src/agents/orchestrator/routing/routing_utils.py
"""
Utilidades para manipulación de estado en routing decisions.

Funciones puras para actualizar GraphStateV2 evitando duplicación
y centralizando lógica de gestión de estado.
"""

import logging
from collections.abc import Sequence
from typing import Any, cast

from src.core.routing_models import RoutingDecision
from src.core.schemas import GraphStateV2

from .intent_parser import detect_explicit_command, is_conversational_only

logger = logging.getLogger(__name__)

# Constantes
CHAT_SPECIALIST_NODE = "chat_specialist"

# Re-exportar para compatibilidad
__all__ = [
    "detect_explicit_command",
    "is_conversational_only",
    "route_to_chat",
    "update_state_with_decision",
    "extract_context_from_state",
    "format_context_for_llm",
]


def route_to_chat(state: GraphStateV2) -> str:
    """Routing fallback a ChatBot specialist."""
    if "payload" not in state:
        state["payload"] = {}

    state["payload"]["next_node"] = CHAT_SPECIALIST_NODE
    logger.debug("Routing fallback a ChatBot")
    return CHAT_SPECIALIST_NODE


def update_state_with_decision(state: GraphStateV2, decision: RoutingDecision) -> None:
    """Actualiza estado del grafo con información de ruteo."""
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
        f"Estado actualizado: {decision.intent} → "
        f"{decision.target_specialist} (confianza: {decision.confidence:.2f})"
    )


def _get_formatted_history(history: Sequence[Any]) -> list[str]:
    """Helper para formatear historial de chat."""
    formatted = []
    # Últimos 5 mensajes para contexto inmediato
    recent = history[-5:] if len(history) >= 5 else history
    for msg in recent:
        # V2ChatMessage puede ser dict o tener atributos
        if isinstance(msg, dict):
            role = "Asistente" if msg.get("role") == "assistant" else "Usuario"
            content = msg.get("content", "")
        else:
            role = "Asistente" if getattr(msg, "role", "") == "assistant" else "Usuario"
            content = getattr(msg, "content", "")

        if content:
            formatted.append(f"{role}: {content}")
    return formatted


def extract_context_from_state(state: GraphStateV2) -> dict[str, Any]:
    """Extrae contexto conversacional del estado."""
    event = state["event"]
    history = state.get("conversation_history", [])
    payload = state.get("payload", {})

    context: dict[str, Any] = {
        "user_id": getattr(event, "user_id", None),
        "history_length": len(history),
        "recent_messages_content": _get_formatted_history(cast(Sequence[Any], history)),
        "previous_intent": payload.get("last_intent") or payload.get("intent"),
        "previous_specialist": payload.get("last_specialist")
        or payload.get("next_node"),
        "session_context": payload.get("session_context"),
    }
    return context


def format_context_for_llm(context: dict[str, Any]) -> str:
    """Formatea contexto para inclusión en prompt LLM."""
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

    if context.get("recent_messages_content"):
        history_str = "\n".join(context["recent_messages_content"])
        parts.append(f"\nÚLTIMOS MENSAJES (Diálogo):\n{history_str}")

    return " | ".join(parts) if parts else "Sesión nueva"
