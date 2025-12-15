# src/core/user_preferences.py
import logging
from typing import Any

from src.core.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class UserPreferences:
    """Gestiona preferencias de usuario en vector memory."""

    def __init__(self, vector_memory_manager: VectorMemoryManager):
        self.vector_manager = vector_memory_manager

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Obtiene preferencias del usuario almacenadas en vector memory."""
        try:
            preferences_results = await self.vector_manager.retrieve_context(
                user_id=user_id,
                query="user preferences and settings",
                context_type=MemoryType.PREFERENCE,
                limit=10
            )

            # Consolidar preferencias
            consolidated_preferences = {}
            for result in preferences_results:
                metadata = result.get("metadata", {})
                if "preferences" in metadata:
                    consolidated_preferences.update(metadata["preferences"])

            logger.info(f"Retrieved preferences for user {user_id}")
            return consolidated_preferences

        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}", exc_info=True)
            return {}

    async def update_user_preferences(
        self,
        user_id: str,
        preferences: dict[str, Any]
    ) -> bool:
        """Actualiza preferencias del usuario."""
        try:
            content = f"User preferences: {', '.join(f'{k}: {v}' for k, v in preferences.items())}"

            return await self.vector_manager.store_context(
                user_id=user_id,
                content=content,
                context_type=MemoryType.PREFERENCE,
                metadata={"preferences": preferences}
            )

        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}", exc_info=True)
            return False
