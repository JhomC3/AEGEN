# src/agents/orchestrator/routing/therapeutic_session.py
"""
Detección y protección de sesiones terapéuticas activas (ADR-0024).

Evita que el Router cambie de especialista CBT durante una crisis
o resistencia terapéutica del usuario.
"""

import logging

from src.core.routing_models import IntentType, RoutingDecision
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Especialistas que activan modo terapéutico
THERAPEUTIC_SPECIALISTS = {"cbt_specialist"}

# Intents que rompen la sesión terapéutica explícitamente
SESSION_BREAKING_INTENTS = {IntentType.TOPIC_SHIFT}


def is_therapeutic_session_active(state: GraphStateV2) -> bool:
    """Verifica si la sesión actual es terapéutica."""
    last_specialist = state.get("payload", {}).get("last_specialist")
    return last_specialist in THERAPEUTIC_SPECIALISTS


def should_maintain_therapeutic_session(
    state: GraphStateV2, decision: RoutingDecision
) -> bool:
    """
    Determina si una decisión de routing debe ser anulada
    para mantener la continuidad de una sesión terapéutica.

    Retorna True si el router quiere cambiar FUERA de CBT
    pero la sesión terapéutica sigue activa y no hay un
    cambio de tema explícito.
    """
    if not is_therapeutic_session_active(state):
        return False

    # Si el router quiere mantener CBT, no hay conflicto
    if decision.target_specialist in THERAPEUTIC_SPECIALISTS:
        return False

    # Permitir salida solo con cambio de tema explícito o comando
    if decision.intent in SESSION_BREAKING_INTENTS:
        return False

    # Cualquier otro caso: mantener sesión terapéutica
    logger.info(
        f"Sesión terapéutica activa: anulando cambio a {decision.target_specialist}. "
        f"Intent '{decision.intent.value}' tratado como resistencia terapéutica."
    )
    return True
