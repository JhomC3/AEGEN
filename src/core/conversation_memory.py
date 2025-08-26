# src/core/conversation_memory.py
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.vector_memory_manager import VectorMemoryManager, MemoryType

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Gestiona memoria conversacional específica integrando Redis + Vector."""

    def __init__(self, vector_memory_manager: VectorMemoryManager):
        self.vector_manager = vector_memory_manager

    async def get_conversation_context(
        self,
        user_id: str,
        chat_id: str,
        include_vector: bool = True,
        include_session: bool = True
    ) -> Dict[str, Any]:
        """Obtiene contexto conversacional completo (Redis + Vector)."""
        context = {
            "user_id": user_id,
            "chat_id": chat_id,
            "vector_context": [],
            "session_context": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            if include_vector:
                vector_context = await self.vector_manager.retrieve_context(
                    user_id=user_id,
                    query=f"conversation context for chat {chat_id}",
                    context_type=MemoryType.CONVERSATION,
                    limit=10
                )
                context["vector_context"] = vector_context
            
            if include_session and self.vector_manager.session_manager:
                session_context = await self.vector_manager.session_manager.get_session(chat_id)
                context["session_context"] = session_context
            
            logger.info(f"Retrieved conversation context for user {user_id}, chat {chat_id}")
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Almacena un turno de conversación en vector memory."""
        try:
            conversation_turn = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "chat_id": chat_id,
                "turn_timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            content_for_embedding = f"Usuario: {user_message}\nAsistente: {assistant_response}"
            
            success = await self.vector_manager.store_context(
                user_id=user_id,
                content=content_for_embedding,
                context_type=MemoryType.CONVERSATION,
                metadata=conversation_turn
            )
            
            if success:
                logger.info(f"Conversation turn stored for user {user_id}, chat {chat_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store conversation turn: {e}", exc_info=True)
            return False