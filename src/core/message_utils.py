from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.core.schemas import V2ChatMessage


def extract_recent_user_messages(messages: list[Any], limit: int = 10) -> list[str]:
    """
    Extrae el contenido de texto de los últimos mensajes humanos para análisis de estilo.
    """
    return [
        str(m.content) for m in messages if isinstance(m, HumanMessage) and m.content
    ][-limit:]


def dict_to_langchain_messages(
    history: list[dict[str, Any]] | list[V2ChatMessage],
    limit: int = 8,
) -> list[BaseMessage]:
    """
    Convierte una lista de diccionarios de mensajes (V2ChatMessage) a objetos BaseMessage de LangChain.

    Args:
        history: Lista de mensajes en formato diccionario/V2ChatMessage.
        limit: Número máximo de mensajes recientes a incluir.

    Returns:
        Lista de objetos BaseMessage (HumanMessage, AIMessage, SystemMessage).
    """
    messages: list[BaseMessage] = []
    # Tomar solo los últimos 'limit' mensajes
    recent_history = history[-limit:] if limit > 0 else history

    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Ignorar mensajes vacíos
        if not content:
            continue

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        # Opcional: Manejar 'function' o 'tool' si es necesario en el futuro

    return messages


def format_history_as_text(
    history: list[dict[str, Any]] | list[V2ChatMessage],
    limit: int = 8,
) -> str:
    """
    Formatea el historial como texto plano (Fallback/Legacy).
    """
    recent_history = history[-limit:] if limit > 0 else history

    return "\n".join([
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
        for m in recent_history
    ])
