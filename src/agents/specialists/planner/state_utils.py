# src/agents/specialists/planner/state_utils.py
"""
Pure functions para manipulación de estado del PlannerAgent.
Siguiendo principios de Clean Architecture - funciones sin side effects.
"""

from src.core.schemas import GraphStateV2, V2ChatMessage


def build_context_from_state(state: GraphStateV2) -> str:
    """
    Construye string de contexto desde GraphStateV2.
    Función pura - no modifica state, solo extrae información.
    """
    event = state["event"]
    payload = state.get("payload", {})

    context_parts = [f"Evento: {event.event_type} desde {event.source}"]

    # Extract content from different sources
    if payload.get("transcript"):
        context_parts.append(f"Transcript: {payload['transcript']}")
    elif event.content:
        context_parts.append(f"Contenido: {event.content}")

    # Include error info if present
    if payload.get("error"):
        context_parts.append(f"Error previo: {payload['error']}")

    return "\n".join(context_parts)


def build_conversation_summary(
    conversation_history: list[V2ChatMessage], max_messages: int = 3
) -> str:
    """
    Construye resumen del historial conversacional.
    Función pura - toma lista, retorna string.
    """
    if not conversation_history:
        return "Sin historial previo"

    recent_messages = conversation_history[-max_messages:]
    summary_parts = [
        f"{msg['role'].capitalize()}: {msg['content'][:50]}..."
        for msg in recent_messages
    ]

    return " | ".join(summary_parts)


def create_user_message(content: str) -> V2ChatMessage:
    """
    Crea mensaje de usuario para historial.
    Función pura - factory function.
    """
    return {"role": "user", "content": content}


def create_assistant_message(content: str) -> V2ChatMessage:
    """
    Crea mensaje de assistant para historial.
    Función pura - factory function.
    """
    return {"role": "assistant", "content": content}


def update_conversation_history(
    current_history: list[V2ChatMessage],
    user_content: str | None,
    assistant_response: str,
) -> list[V2ChatMessage]:
    """
    Actualiza historial conversacional con nuevo intercambio.
    Función pura - retorna nueva lista sin modificar la original.
    """
    updated_history = list(current_history)

    # Add user message if content exists
    if user_content:
        updated_history.append(create_user_message(user_content))

    # Always add assistant response
    updated_history.append(create_assistant_message(assistant_response))

    return updated_history


def extract_user_content_from_state(state: GraphStateV2) -> str | None:
    """
    Extrae contenido del usuario desde el state.
    Función pura - extraction logic encapsulada.
    """
    payload = state.get("payload", {})

    # Priority: transcript > event content
    if payload.get("transcript"):
        return payload["transcript"]
    elif state["event"].content:
        return str(state["event"].content)

    return None
