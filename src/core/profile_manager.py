import json
import logging
from datetime import datetime
from typing import Any

from src.core.dependencies import get_sqlite_store
from src.core.localization import get_country_info, resolve_localization

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

        Uses Pydantic model_validate to fill in missing sections with defaults.
        Preserves all existing data. Bumps version to current.
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
        Inicializa la identidad con datos de la plataforma (Telegram),
        pero SOLO si el nombre actual sigue siendo el default "Usuario".
        Esto evita sobrescribir un nombre que el usuario ya nos haya dado explícitamente.
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
        from src.core.dependencies import redis_connection

        # 1. Intentar desde Redis (Caché caliente)
        if redis_connection:
            key = self._redis_key(chat_id)
            try:
                raw_data = await redis_connection.get(key)
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
                if redis_connection:
                    key = self._redis_key(chat_id)
                    await redis_connection.set(
                        key, json.dumps(complete, ensure_ascii=False)
                    )
                return complete
        except Exception as e:
            logger.error(f"Error cargando perfil de SQLite para {chat_id}: {e}")

        # 3. Fallback: Default
        logger.info(f"Perfil no encontrado para {chat_id}. Usando default.")
        return self._get_default_profile()

    async def save_profile(self, chat_id: str, profile: dict[str, Any]):
        """
        3.7: Guarda el perfil en Redis y SQLite (Local-First).
        """
        from src.core.dependencies import redis_connection

        profile["metadata"]["last_updated"] = datetime.now().isoformat()

        # 1. Guardar en Redis (Caché caliente)
        if redis_connection:
            key = self._redis_key(chat_id)
            try:
                payload = json.dumps(profile, ensure_ascii=False)
                await redis_connection.set(key, payload)
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
    ):
        """3.9: Registra cambios en el timeline y evolución."""
        profile = await self.load_profile(chat_id)
        now = datetime.now().isoformat()

        entry = {
            "date": now,
            "event": event,
            "type": type,
        }
        profile["timeline"].append(entry)
        profile["evolution"]["path_traveled"].append(entry)

        if type == "milestone":
            profile["evolution"]["milestones_count"] += 1

        await self.save_profile(chat_id, profile)

    def get_context_for_prompt(self, profile: dict[str, Any]) -> dict[str, str]:
        """Retorna contexto formateado desde el objeto perfil pasado."""
        psy = profile.get("psychological_state", {})
        val = profile.get("values_and_goals", {})

        metaphors = ", ".join(psy.get("key_metaphors", [])) or "None"
        struggles = ", ".join(psy.get("active_struggles", [])) or "None"
        values = ", ".join(val.get("core_values", [])) or "None"

        return {
            "phase": psy.get("current_phase", "Discovery"),
            "metaphors": metaphors,
            "struggles": struggles,
            "values": values,
            "goals": ", ".join(val.get("short_term_goals", [])) or "None",
        }

    def get_active_tags(self, profile: dict[str, Any]) -> list[str]:
        return profile.get("active_tags", [])

    def get_style(self, profile: dict[str, Any]) -> str:
        return profile.get("identity", {}).get("style", "Casual y Directo")

    def get_personality_adaptation(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Retorna la configuración de adaptación de personalidad."""
        return profile.get(
            "personality_adaptation",
            {
                "preferred_style": "casual",
                "communication_level": "intermediate",
                "humor_tolerance": 0.7,
                "formality_level": 0.3,
                "history_limit": 20,
                "learned_preferences": [],
            },
        )

    async def update_localization(self, chat_id: str, language_code: str | None):
        """
        C.9: Actualiza la información de localización en el perfil (Pasivo).
        Optimizado para no disparar sync a cloud innecesarios.
        """
        if not language_code:
            return

        profile = await self.load_profile(chat_id)
        loc = profile.get("localization", {})

        # Si ya fue confirmado por el usuario, no sobrescribimos con data pasiva
        if loc.get("confirmed_by_user"):
            return

        # Solo actualizar si es nuevo o diferente
        if loc.get("language_code") == language_code:
            return

        # Resolver nueva localización
        new_loc = resolve_localization(language_code)
        new_loc["language_code"] = language_code
        new_loc["confirmed_by_user"] = False

        profile["localization"] = new_loc

        # Guardar solo en Redis (Optimización Fase 3)
        from src.core.dependencies import redis_connection

        if redis_connection:
            profile["metadata"]["last_updated"] = datetime.now().isoformat()
            key = self._redis_key(chat_id)
            await redis_connection.set(key, json.dumps(profile, ensure_ascii=False))

        logger.debug(
            f"Localización pasiva para {chat_id}: {language_code} -> {new_loc['dialect']}"
        )

    async def update_location_from_user_input(
        self, chat_id: str, country_code: str, region: str | None = None
    ):
        """
        Actualiza localización basada en entrada explícita del usuario.
        Esta actualización SI se sincroniza con la nube.
        """
        profile = await self.load_profile(chat_id)
        loc = profile.get("localization", {})

        country_info = get_country_info(country_code)
        if not country_info:
            logger.warning(f"País no soportado: {country_code}")
            return

        loc["country_code"] = country_code.upper()
        loc["confirmed_by_user"] = True

        if region and region.lower() in country_info["regions"]:
            reg_info = country_info["regions"][region.lower()]
            loc["region"] = region.lower()
            loc["dialect_hint"] = reg_info["dialect_hint"]
            loc["timezone"] = reg_info["timezone"]
        else:
            loc["region"] = None
            loc["dialect_hint"] = None
            loc["timezone"] = country_info["timezone"]

        loc["dialect"] = country_info["dialect"]

        profile["localization"] = loc
        await self.save_profile(chat_id, profile)
        logger.info(
            f"Localización confirmada por usuario para {chat_id}: {country_code}, {region}"
        )


# Singleton (Stateless Manager)
user_profile_manager = UserProfileManager()
