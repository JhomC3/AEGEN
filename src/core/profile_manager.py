import json
import logging
from datetime import datetime
from typing import Any

from src.core import dependencies
from src.core.dependencies import get_sqlite_store
from src.core.profile_context import get_personality_adaptation
from src.core.profile_evolution import add_evolution_entry
from src.core.profile_localization import (
    update_localization_passive,
    update_location_from_user_input,
)
from src.core.profile_seeder import ensure_profile_complete, get_default_profile

logger = logging.getLogger(__name__)


class UserProfileManager:
    """
    Gestiona el perfil evolutivo y diskless del usuario.
    """

    def __init__(self) -> None:
        logger.info("UserProfileManager initialized")

    def _redis_key(self, chat_id: str) -> str:
        """Retorna la clave de Redis para el perfil."""
        return f"profile:{chat_id}"

    async def load_profile(self, chat_id: str) -> dict[str, Any]:
        """Carga el perfil desde Redis o SQLite."""
        if dependencies.redis_connection:
            key = self._redis_key(chat_id)
            try:
                raw_data = await dependencies.redis_connection.get(key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    return ensure_profile_complete(json.loads(raw_data))
            except Exception as e:
                logger.error("Error Redis %s: %s", chat_id, e)

        try:
            store = get_sqlite_store()
            sqlite_profile = await store.load_profile(chat_id)
            if sqlite_profile:
                complete = ensure_profile_complete(sqlite_profile)
                if dependencies.redis_connection:
                    key = self._redis_key(chat_id)
                    await dependencies.redis_connection.set(
                        key, json.dumps(complete, ensure_ascii=False)
                    )
                return complete
        except Exception as e:
            logger.error("Error SQLite %s: %s", chat_id, e)

        return get_default_profile()

    async def save_profile(self, chat_id: str, profile: dict[str, Any]) -> None:
        """Guarda el perfil en Redis y SQLite."""
        profile["metadata"]["last_updated"] = datetime.now().isoformat()

        if dependencies.redis_connection:
            key = self._redis_key(chat_id)
            try:
                payload = json.dumps(profile, ensure_ascii=False)
                await dependencies.redis_connection.set(key, payload)
            except Exception as e:
                logger.error("Error save Redis %s: %s", chat_id, e)

        try:
            store = get_sqlite_store()
            await store.save_profile(chat_id, profile)
        except Exception as e:
            logger.error("Error save SQLite %s: %s", chat_id, e)

    # --- Métodos de Delegación ---

    async def update_localization(
        self, chat_id: str, language_code: str | None
    ) -> None:
        """Actualiza la localización pasiva."""
        profile = await self.load_profile(chat_id)
        if update_localization_passive(profile, language_code):
            await self.save_profile(chat_id, profile)

    async def update_location_from_user_input(
        self, chat_id: str, country_code: str, region: str | None
    ) -> None:
        """Actualiza la ubicación confirmada."""
        profile = await self.load_profile(chat_id)
        if update_location_from_user_input(profile, country_code, region):
            await self.save_profile(chat_id, profile)

    def get_personality_adaptation(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Proxy para get_personality_adaptation."""
        return get_personality_adaptation(profile)

    async def add_evolution_entry(
        self, chat_id: str, event: str, entry_type: str = "milestone"
    ) -> None:
        """Agrega entrada de evolución al perfil."""
        profile = await self.load_profile(chat_id)
        add_evolution_entry(profile, event, entry_type)
        await self.save_profile(chat_id, profile)

    async def list_all_profiles(self) -> list[str]:
        """Retorna todos los chat_ids registrados."""
        try:
            store = get_sqlite_store()
            return await store.list_all_chat_ids()
        except Exception as e:
            logger.error("Error list perfiles: %s", e)
            return []

    async def seed_identity_from_platform(
        self, chat_id: str, first_name: str | None
    ) -> None:
        """Inicializa la identidad con datos de la plataforma."""
        if not first_name:
            return

        try:
            profile = await self.load_profile(chat_id)
            identity = profile.get("identity", {})
            current_name = identity.get("name", "Usuario")

            if current_name == "Usuario" or not current_name:
                logger.info("Seed %s: %s", chat_id, first_name)
                identity["name"] = first_name
                await self.save_profile(chat_id, profile)
        except Exception as e:
            logger.error("Seed error %s: %s", chat_id, e)


# Global instance
user_profile_manager = UserProfileManager()
