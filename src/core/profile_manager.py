import json
import logging
from datetime import datetime
from typing import Any

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
        """
        3.2: Estructura de perfil expandida (Valores, Metas, Evolución).
        """
        now = datetime.now().isoformat()
        return {
            "identity": {
                "name": "Usuario",
                "style": "Casual y Directo",
                "preferences": {},
            },
            "personality_adaptation": {
                "preferred_style": "casual",
                "communication_level": "intermediate",
                "humor_tolerance": 0.7,
                "formality_level": 0.3,
                "history_limit": 20,
                "learned_preferences": [],
                "active_topics": [],
            },
            "psychological_state": {
                "current_phase": "Discovery",
                "key_metaphors": [],
                "active_struggles": [],
            },
            "values_and_goals": {
                "core_values": [],
                "short_term_goals": [],
                "long_term_dreams": [],
                "physical_state": "Not specified",
            },
            "tasks_and_activities": {"active_tasks": [], "completed_activities": []},
            "evolution": {
                "level": 1,
                "milestones_count": 0,
                "path_traveled": [],  # Registro del "camino recorrido"
            },
            "active_tags": ["bienvenida"],
            "localization": {
                "country_code": None,  # ISO (ej: "CO")
                "region": None,  # Ciudad/Región (ej: "medellin")
                "timezone": "UTC",  # IANA Timezone
                "language_code": None,  # Código de Telegram
                "dialect": "neutro",  # Dialecto derivado
                "dialect_hint": None,  # Matiz regional (ej: "paisa")
                "confirmed_by_user": False,  # Si el usuario lo validó
            },
            "timeline": [
                {
                    "date": now,
                    "event": "Creación de Perfil Evolutivo",
                    "type": "system",
                }
            ],
            "metadata": {
                "version": "1.1.0",
                "last_updated": now,
            },
        }

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
        Si no existe, intenta recuperación determinística desde la nube (Gateway).
        """
        from src.core.dependencies import redis_connection
        from src.memory.cloud_gateway import cloud_gateway

        if redis_connection is None:
            logger.warning("Redis no disponible, usando perfil default.")
            return self._get_default_profile()

        key = self._redis_key(chat_id)
        try:
            raw_data = await redis_connection.get(key)
            if raw_data:
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                return json.loads(raw_data)
        except Exception as e:
            logger.error(f"Error cargando perfil de Redis para {chat_id}: {e}")

        # --- AUTO-RECUPERACIÓN UNIFICADA (Gateway) ---
        logger.info(
            f"Perfil no encontrado en Redis para {chat_id}. Recuperando de Cloud..."
        )
        recovered_profile = await cloud_gateway.download_memory(chat_id, "user_profile")

        if recovered_profile:
            # Rehidratar Redis para futuras consultas
            await self.save_profile(chat_id, recovered_profile)
            return recovered_profile

        # Si falla la recuperación, retornamos default
        logger.info(f"Recuperación fallida para {chat_id}. Usando default.")
        return self._get_default_profile()

    async def save_profile(self, chat_id: str, profile: dict[str, Any]):
        """
        3.7: Guarda el perfil en Redis y dispara sincronización unificada a la nube.
        """
        from src.core.dependencies import redis_connection
        from src.memory.cloud_gateway import cloud_gateway

        if redis_connection is None:
            return

        profile["metadata"]["last_updated"] = datetime.now().isoformat()
        key = self._redis_key(chat_id)

        try:
            # 1. Guardar en Redis
            payload = json.dumps(profile, ensure_ascii=False)
            await redis_connection.set(key, payload)

            # 2. Sincronización Unificada (Markdown + YAML)
            import asyncio

            asyncio.create_task(
                cloud_gateway.upload_memory(
                    chat_id=chat_id,
                    filename="user_profile",
                    data=profile,
                    mem_type="user_profile",
                )
            )

        except Exception as e:
            logger.error(f"Error guardando perfil para {chat_id}: {e}")

    async def sync_to_cloud(self, chat_id: str, profile: dict[str, Any]):
        """
        OBSOLETO: Se mantiene por compatibilidad temporal pero redirige al Gateway.
        """
        from src.memory.cloud_gateway import cloud_gateway

        await cloud_gateway.upload_memory(
            chat_id, "user_profile", profile, "user_profile"
        )

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
