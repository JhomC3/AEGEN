# src/core/session_manager.py
"""
SessionManager for GraphStateV2 persistence in Redis.
Handles conversational memory storage with TTL and serialization.
"""

import json
import logging
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel

from .config import settings
from .schemas import V2ChatMessage

logger = logging.getLogger(__name__)


class ConversationSession(BaseModel):
    """
    Serializable session data for Redis storage.
    Represents the persistent state of a conversation.
    """

    chat_id: str
    conversation_history: list[V2ChatMessage]
    last_update: str  # ISO timestamp
    metadata: dict[str, Any] = {}


class SessionManager:
    """
    Manages conversational session persistence in Redis.

    Responsibilities:
    - Store/retrieve GraphStateV2 conversation_history
    - Handle TTL and session cleanup
    - JSON serialization/deserialization
    - Error handling and fallback
    """

    def __init__(self, redis_url: str | None = None, ttl: int | None = None):
        """
        Initialize SessionManager with Redis connection.

        Args:
            redis_url: Redis connection URL (defaults to settings)
            ttl: Session TTL in seconds (defaults to settings)
        """
        self.redis_url = redis_url or settings.REDIS_SESSION_URL
        self.ttl = ttl or settings.REDIS_SESSION_TTL
        self._redis: redis.Redis | None = None

        logger.info(f"SessionManager initialized with TTL: {self.ttl}s")

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
            await self._redis.ping()  # Test connection
            logger.info("SessionManager: Redis connection established")
        return self._redis

    def _session_key(self, chat_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:chat:{chat_id}"

    async def get_session(self, chat_id: str) -> dict[str, Any] | None:
        """
        Retrieve session state from Redis.

        Args:
            chat_id: Chat identifier

        Returns:
            Dict with conversation_history or None if not found
        """
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            session_data = await redis_client.get(key)
            if not session_data:
                logger.debug(f"No session found for chat_id: {chat_id}")
                return None

            # Deserialize session
            session_dict = json.loads(session_data)
            session = ConversationSession(**session_dict)

            # Return only the conversation history - caller will build GraphStateV2
            session_info = {
                "conversation_history": session.conversation_history,
            }

            logger.info(
                f"Session retrieved for chat_id: {chat_id}, {len(session.conversation_history)} messages"
            )
            return session_info

        except Exception as e:
            logger.error(f"Failed to get session for {chat_id}: {e}", exc_info=True)
            return None

    async def save_session(self, chat_id: str, state: dict[str, Any]) -> bool:
        """
        Save session state to Redis.

        Args:
            chat_id: Chat identifier
            state: Dict containing conversation_history

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            # Extract conversation history
            conversation_history = state.get("conversation_history", [])

            # Create session object
            from datetime import datetime

            session = ConversationSession(
                chat_id=chat_id,
                conversation_history=conversation_history,
                last_update=datetime.utcnow().isoformat(),
                metadata={
                    "last_event_type": getattr(state.get("event"), "event_type", None),
                    "payload_keys": list(state.get("payload", {}).keys()),
                },
            )

            # Serialize and save
            session_data = session.model_dump_json()
            await redis_client.setex(key, self.ttl, session_data)

            logger.info(
                f"Session saved for chat_id: {chat_id}, {len(conversation_history)} messages, TTL: {self.ttl}s"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save session for {chat_id}: {e}", exc_info=True)
            return False

    async def delete_session(self, chat_id: str) -> bool:
        """
        Delete session from Redis.

        Args:
            chat_id: Chat identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            result = await redis_client.delete(key)
            logger.info(
                f"Session deleted for chat_id: {chat_id}, existed: {bool(result)}"
            )
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete session for {chat_id}: {e}", exc_info=True)
            return False

    async def get_session_info(self, chat_id: str) -> dict[str, Any] | None:
        """
        Get session metadata without full conversation history.

        Args:
            chat_id: Chat identifier

        Returns:
            Session metadata dict or None if not found
        """
        try:
            redis_client = await self._get_redis()
            key = self._session_key(chat_id)

            session_data = await redis_client.get(key)
            if not session_data:
                return None

            session_dict = json.loads(session_data)
            session = ConversationSession(**session_dict)

            # Get TTL
            ttl = await redis_client.ttl(key)

            return {
                "chat_id": session.chat_id,
                "message_count": len(session.conversation_history),
                "last_update": session.last_update,
                "ttl_seconds": ttl,
                "metadata": session.metadata,
            }

        except Exception as e:
            logger.error(
                f"Failed to get session info for {chat_id}: {e}", exc_info=True
            )
            return None

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("SessionManager: Redis connection closed")


# Global singleton instance
session_manager = SessionManager()
