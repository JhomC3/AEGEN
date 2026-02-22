# src/core/session_utils.py
from datetime import datetime
from typing import Any

from src.core.schemas.session import ConversationSession


def calculate_adaptive_ttl(state: dict[str, Any]) -> int:
    """
    Calcula el TTL adaptativo basado en el contexto de la sesión.
    - 24h para sesiones de terapia (cbt_specialist)
    - 8h para conversaciones largas (>10 mensajes)
    - 4h base para el resto
    """
    last_specialist = state.get("payload", {}).get("last_specialist")
    history_len = len(state.get("conversation_history", []))

    if last_specialist == "cbt_specialist":
        return 86400  # 24 horas
    if history_len > 10:
        return 28800  # 8 horas

    return 14400  # 4 horas


def build_conversation_session(
    chat_id: str, state: dict[str, Any], max_history: int = 30
) -> ConversationSession:
    """Construye el objeto ConversationSession aplicando truncamiento."""
    conversation_history = state.get("conversation_history", [])
    original_len = len(conversation_history)

    if original_len > max_history:
        conversation_history = conversation_history[-max_history:]

    payload = state.get("payload", {})

    return ConversationSession(
        chat_id=chat_id,
        conversation_history=conversation_history,
        last_update=datetime.utcnow().isoformat(),
        last_specialist=payload.get("last_specialist"),
        last_intent=payload.get("intent"),
        session_context=payload.get("session_context", {}),
        metadata={
            "last_event_type": getattr(state.get("event"), "event_type", None),
            "history_truncated": original_len > max_history,
        },
    )
