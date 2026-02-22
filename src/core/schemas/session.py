from typing import Any

from pydantic import BaseModel

from src.core.schemas.graph import V2ChatMessage


class ConversationSession(BaseModel):
    """
    Serializable session data for Redis storage.
    Represents the persistent state of a conversation.
    """

    chat_id: str
    conversation_history: list[V2ChatMessage]
    last_update: str  # ISO timestamp
    last_specialist: str | None = None
    last_intent: str | None = None
    session_context: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
