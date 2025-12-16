# src/agents/orchestrator/routing/routing_utils.py
"""
Utilidades para manipulación de estado en routing decisions.

Funciones puras para actualizar GraphStateV2 evitando duplicación
y centralizando lógica de gestión de estado.
"""

import logging
from typing import Any

from src.core.routing_models import RoutingDecision
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Constantes
CHAT_SPECIALIST_NODE = "chat_specialist"
PAYLOAD_KEY = "payload"
NEXT_NODE_KEY = "next_node"


def route_to_chat(state: GraphStateV2) -> str:
    """
    Routing fallback a ChatBot specialist.

    Args:
        state: Estado del grafo a modificar

    Returns:
        str: Nombre del nodo ChatBot specialist
    """
    if PAYLOAD_KEY not in state:
        state[PAYLOAD_KEY] = {}

    state[PAYLOAD_KEY][NEXT_NODE_KEY] = CHAT_SPECIALIST_NODE
    logger.debug("Routing fallback a ChatBot")
    return CHAT_SPECIALIST_NODE


def update_state_with_decision(state: GraphStateV2, decision: RoutingDecision) -> None:
    """
    Actualiza estado del grafo con información de routing decision.

    Args:
        state: Estado del grafo a modificar
        decision: Decisión de routing con metadata completa
    """
    if PAYLOAD_KEY not in state:
        state[PAYLOAD_KEY] = {}

    payload = state[PAYLOAD_KEY]
    payload.update({
        NEXT_NODE_KEY: decision.target_specialist,
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
    event = state.get("event", {})
    history = state.get("conversation_history", [])

    context = {}

    # Información del usuario
    if hasattr(event, "user_id"):
        context["user_id"] = event.user_id

    # Historial conversacional
    if history:
        context["history_length"] = len(history)
        # Últimos 2 mensajes para contexto inmediato
        recent_messages = history[-2:] if len(history) >= 2 else history
        context["recent_interactions"] = len(recent_messages)
    else:
        context["history_length"] = 0
        context["recent_interactions"] = 0

    return context
