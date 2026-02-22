import json
import logging
from typing import Any

import redis.asyncio as redis

from src.core.schemas.session import ConversationSession
from src.core.session_consolidation import trigger_session_consolidation
from src.core.session_utils import (
    build_conversation_session,
    calculate_adaptive_ttl,
)

from .config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversational session persistence in Redis.
    """

    def __init__(self, redis_url: str | None = None, ttl: int | None = None) -> None:
        self.redis_url = redis_url or settings.REDIS_SESSION_URL
        self.ttl = ttl or settings.REDIS_SESSION_TTL
        self._redis: redis.Redis | None = None

        logger.info(f"SessionManager initialized with TTL: {self.ttl}s")

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
            await self._redis.ping()
            logger.info("SessionManager: Redis connection established")
        return self._redis

    def _session_key(self, chat_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:chat:{chat_id}"

    async def get_session(self, chat_id: str) -> dict[str, Any] | None:
        """Retrieve session state from Redis."""
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            session_data = await redis_client.get(key)
            if not session_data:
                logger.debug(f"No session found for chat_id: {chat_id}")
                return None

            session_dict = json.loads(session_data)
            session = ConversationSession(**session_dict)

            logger.info(
                f"Session retrieved for chat_id: {chat_id}, "
                f"{len(session.conversation_history)} messages"
            )
            return {
                "conversation_history": session.conversation_history,
                "last_specialist": session.last_specialist,
                "last_intent": session.last_intent,
                "session_context": session.session_context,
            }

        except Exception as e:
            logger.error(f"Failed to get session for {chat_id}: {e}", exc_info=True)
            return None

    async def save_session(self, chat_id: str, state: dict[str, Any]) -> bool:
        """Save session state to Redis."""
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            # Usar utilidades extraídas
            ttl = calculate_adaptive_ttl(state)
            session = build_conversation_session(chat_id, state)

            await redis_client.setex(key, ttl, session.model_dump_json())

            logger.info(
                f"Session saved for {chat_id}, {len(session.conversation_history)}"
                f" msgs, Specialist: {session.last_specialist}, TTL: {ttl}s"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save session for {chat_id}: {e}", exc_info=True)
            return False

    async def delete_session(self, chat_id: str) -> bool:
        """Delete session from Redis."""
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            result = await redis_client.delete(key)
            logger.info(f"Session deleted for {chat_id}, existed: {bool(result)}")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete session for {chat_id}: {e}", exc_info=True)
            return False

    async def trigger_consolidation(self, chat_id: str) -> None:
        """Triggers session consolidation."""
        session = await self.get_session(chat_id)
        await trigger_session_consolidation(chat_id, session)

    async def get_session_info(self, chat_id: str) -> dict[str, Any] | None:
        """Get session metadata without history."""
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            session_data = await redis_client.get(key)
            if not session_data:
                return None

            session = ConversationSession(**json.loads(session_data))
            ttl = await redis_client.ttl(key)

            return {
                "chat_id": session.chat_id,
                "message_count": len(session.conversation_history),
                "last_update": session.last_update,
                "ttl_seconds": ttl,
                "metadata": session.metadata,
            }
        except Exception as e:
            logger.error(f"Failed to get info for {chat_id}: {e}", exc_info=True)
            return None

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("SessionManager: Redis connection closed")


# Global singleton instance
session_manager = SessionManager()
