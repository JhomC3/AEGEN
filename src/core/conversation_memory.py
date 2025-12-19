# src/core/conversation_memory.py
import logging
from datetime import datetime
from typing import Any

from src.core.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Gestiona memoria conversacional usando Redis (SessionManager)."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def get_conversation_context(
        self,
        user_id: str,
        chat_id: str,
        include_vector: bool = False,  # Deprecated, kept for compatibility
        include_session: bool = True,
    ) -> dict[str, Any]:
        """Obtiene contexto conversacional (Solo Redis)."""
        context: dict[str, Any] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "vector_context": [],  # Empty as vector DB is removed
            "session_context": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if include_session and self.session_manager:
                session_context = await self.session_manager.get_session(chat_id)
                context["session_context"] = session_context

            logger.info(
                f"Retrieved conversation context for user {user_id}, chat {chat_id}"
            )
            return context

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}", exc_info=True)
            return context

    async def store_conversation_turn(
        self,
        user_id: str,
        chat_id: str,
        user_message: str,
        assistant_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Almacena un turno de conversación.
        Nota: La persistencia histórica en vector DB ha sido eliminada.
        Redis maneja el historial reciente automáticamente en SessionManager.
        """
        # No-op para almacenamiento permanente
        return True
