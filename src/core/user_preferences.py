import logging
from typing import Any

from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class UserPreferences:
    """Gestiona preferencias de usuario en vector memory."""

    def __init__(self, vector_memory_manager: VectorMemoryManager):
        self.vector_manager = vector_memory_manager

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Obtiene preferencias del usuario."""
        try:
            results = await self.vector_manager.retrieve_context(
                user_id=user_id,
                query="user preferences and settings",
                context_type=MemoryType.PREFERENCE,
                limit=10,
            )

            consolidated_preferences = {}
            for result in results:
                metadata = result.get("metadata", {})
                if "preferences" in metadata:
                    consolidated_preferences.update(metadata["preferences"])

            logger.info("Retrieved preferences for %s", user_id)
            return consolidated_preferences

        except Exception as e:
            logger.error("Failed to get preferences for %s: %s", user_id, e)
            return {}

    async def update_user_preferences(
        self, user_id: str, preferences: dict[str, Any]
    ) -> bool:
        """Actualiza preferencias del usuario."""
        try:
            parts = [f"{k}: {v}" for k, v in preferences.items()]
            content = f"User preferences: {', '.join(parts)}"

            stored_count = await self.vector_manager.store_context(
                user_id=user_id,
                content=content,
                context_type=MemoryType.PREFERENCE,
                metadata={"type": "preference_update"},
            )
            return stored_count > 0

        except Exception as e:
            logger.error("Failed to update preferences for %s: %s", user_id, e)
            return False
