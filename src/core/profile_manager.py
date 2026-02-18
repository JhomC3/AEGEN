import json
import logging
from datetime import datetime
from typing import Any

from src.core import dependencies
from src.core.dependencies import get_sqlite_store
from src.core.profile_context import (
    get_active_tags,
    get_context_for_prompt,
    get_personality_adaptation,
    get_style,
)
from src.core.profile_evolution import add_evolution_entry
from src.core.profile_localization import (
    update_localization_passive,
    update_location_from_user_input,
)

logger = logging.getLogger(__name__)


class UserProfileManager:
    """
    Gestiona el perfil evolutivo y diskless del usuario (Redis + Google Cloud).
    Refactorizado para soporte multi-usuario y arquitectura sin disco.
    """

    def __init__(self):
        logger.info("UserProfileManager initialized (Diskless & Multi-user)")

    def _get_default_profile(self) -> dict[str, Any]:
        """Returns a complete default profile using the Pydantic model."""
        from src.core.schemas.profile import UserProfile

        return UserProfile().model_dump()

    def _ensure_complete(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Validates and migrates an old profile dict.
        """
        from src.core.schemas.profile import UserProfile

        try:
            profile = UserProfile.model_validate(raw)
            # Ensure version is bumped to latest
            profile.metadata.version = "1.2.0"
            return profile.model_dump()
        except Exception as e:
            logger.warning(f"Profile migration failed, using merged approach: {e}")
            # Fallback: merge old dict onto defaults
            defaults = self._get_default_profile()
            for key, value in raw.items():
                if (
                    isinstance(value, dict)
                    and key in defaults
                    and isinstance(defaults[key], dict)
                ):
                    defaults[key].update(value)
                else:
                    defaults[key] = value
            return defaults

    def _redis_key(self, chat_id: str) -> str:
        """3.4: Retorna la clave de Redis para el perfil."""
        return f"profile:{chat_id}"

    async def seed_identity_from_platform(
        self, chat_id: str, first_name: str | None
    ) -> None:
        """
        Inicializa la identidad con datos de la plataforma (Telegram).
        """
        if not first_name:
            return

        try:
            profile = await self.load_profile(chat_id)
            current_name = profile.get("identity", {}).get("name", "Usuario")

            # Solo actualizamos si el nombre es el default o está vacío
            if current_name == "Usuario" or not current_name:
                logger.info(
                    f"Seeding identity from platform for {chat_id}: {first_name}"
                )
                profile["identity"]["name"] = first_name
                await self.save_profile(chat_id, profile)
        except Exception as e:
            logger.error(f"Error seeding identity for {chat_id}: {e}")

    async def load_profile(self, chat_id: str) -> dict[str, Any]:
        """
        3.6: Carga el perfil desde Redis (Caché caliente).
        Si no existe, intenta recuperación desde SQLite (Local-First).
        """
        # 1. Intentar desde Redis (Caché caliente)
        if dependencies.redis_connection:
            key = self._redis_key(chat_id)
            try:
                raw_data = await dependencies.redis_connection.get(key)
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    return self._ensure_complete(json.loads(raw_data))
            except Exception as e:
                logger.error(f"Error cargando perfil de Redis para {chat_id}: {e}")

        # 2. Intentar desde SQLite (Persistencia Local)
        try:
            store = get_sqlite_store()
            sqlite_profile = await store.load_profile(chat_id)
            if sqlite_profile:
                complete = self._ensure_complete(sqlite_profile)
                # Rehidratar Redis para futuras consultas
                if dependencies.redis_connection:
                    key = self._redis_key(chat_id)
                    await dependencies.redis_connection.set(
                        key, json.dumps(complete, ensure_ascii=False)
                    )
                return complete
        except Exception as e:
            logger.error(f"Error cargando perfil de SQLite para {chat_id}: {e}")

        # 3. Fallback: Default
        logger.info(f"Perfil no encontrado para {chat_id}. Usando default.")
        return self._get_default_profile()

    async def list_all_profiles(self) -> list[str]:
        """Retorna todos los chat_ids registrados en la persistencia local."""
        try:
            store = get_sqlite_store()
            return await store.list_all_chat_ids()
        except Exception as e:
            logger.error(f"Error listando perfiles: {e}")
            return []

    async def save_profile(self, chat_id: str, profile: dict[str, Any]) -> None:
        """
        3.7: Guarda el perfil en Redis y SQLite (Local-First).
        """
        profile["metadata"]["last_updated"] = datetime.now().isoformat()

        # 1. Guardar en Redis (Caché caliente)
        if dependencies.redis_connection:
            key = self._redis_key(chat_id)
            try:
                payload = json.dumps(profile, ensure_ascii=False)
                await dependencies.redis_connection.set(key, payload)
            except Exception as e:
                logger.error(f"Error guardando perfil en Redis para {chat_id}: {e}")

        # 2. Guardar en SQLite (Persistencia Local-First)
        try:
            store = get_sqlite_store()
            await store.save_profile(chat_id, profile)
            logger.debug(f"Perfil guardado en SQLite para {chat_id}")
        except Exception as e:
            logger.error(f"Error guardando perfil en SQLite para {chat_id}: {e}")

    async def add_evolution_entry(
        self, chat_id: str, event: str, type: str = "milestone"
    ) -> None:
        """3.9: Registra cambios en el timeline y evolución."""
        profile = await self.load_profile(chat_id)
        add_evolution_entry(profile, event, type)
        await self.save_profile(chat_id, profile)

    def get_context_for_prompt(self, profile: dict[str, Any]) -> dict[str, str]:
        """Retorna contexto formateado desde el objeto perfil pasado."""
        return get_context_for_prompt(profile)

    def get_active_tags(self, profile: dict[str, Any]) -> list[str]:
        return get_active_tags(profile)

    def get_style(self, profile: dict[str, Any]) -> str:
        return get_style(profile)

    def get_personality_adaptation(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Retorna la configuración de adaptación de personalidad."""
        return get_personality_adaptation(profile)

    async def update_localization(
        self, chat_id: str, language_code: str | None
    ) -> None:
        """
        C.9: Actualiza la información de localización en el perfil (Pasivo).
        """
        profile = await self.load_profile(chat_id)

        if update_localization_passive(profile, language_code):
            # Guardar solo en Redis (Optimización Fase 3)
            if dependencies.redis_connection:
                profile["metadata"]["last_updated"] = datetime.now().isoformat()
                key = self._redis_key(chat_id)
                await dependencies.redis_connection.set(
                    key, json.dumps(profile, ensure_ascii=False)
                )

            loc = profile.get("localization", {})
            logger.debug(
                f"Localización pasiva para {chat_id}: {language_code} -> {loc.get('dialect')}"
            )

    async def update_location_from_user_input(
        self, chat_id: str, country_code: str, region: str | None = None
    ) -> None:
        """
        Actualiza localización basada en entrada explícita del usuario.
        """
        profile = await self.load_profile(chat_id)

        if update_location_from_user_input(profile, country_code, region):
            await self.save_profile(chat_id, profile)
            logger.info(
                f"Localización confirmada por usuario para {chat_id}: {country_code}, {region}"
            )


# Singleton (Stateless Manager)
user_profile_manager = UserProfileManager()
