import json
import logging
from datetime import datetime
from typing import Any

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
            "timeline": [
                {
                    "date": now,
                    "event": "Creación de Perfil Evolutivo",
                    "type": "system",
                }
            ],
            "metadata": {
                "version": "1.0.0",
                "last_updated": now,
            },
        }

    def _redis_key(self, chat_id: str) -> str:
        """3.4: Retorna la clave de Redis para el perfil."""
        return f"profile:{chat_id}"

    async def load_profile(self, chat_id: str) -> dict[str, Any]:
        """
        3.6: Carga el perfil desde Redis (Caché caliente).
        Si no existe, retorna el default.
        """
        from src.core.dependencies import redis_connection

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

        # Si no existe en Redis, retornamos default (Phase 3.6 - Cloud fallback pending)
        logger.info(f"Perfil no encontrado para {chat_id}. Usando default.")
        return self._get_default_profile()

    async def save_profile(self, chat_id: str, profile: dict[str, Any]):
        """
        3.7: Guarda el perfil en Redis y dispara sincronización a la nube.
        """
        from src.core.dependencies import redis_connection

        if redis_connection is None:
            return

        profile["metadata"]["last_updated"] = datetime.now().isoformat()
        key = self._redis_key(chat_id)

        try:
            # 1. Guardar en Redis
            payload = json.dumps(profile, ensure_ascii=False)
            await redis_connection.set(key, payload)

            # 2. 3.8: Sync a Google Cloud (Background)
            import asyncio

            asyncio.create_task(self.sync_to_cloud(chat_id, profile))

        except Exception as e:
            logger.error(f"Error guardando perfil para {chat_id}: {e}")

    async def sync_to_cloud(self, chat_id: str, profile: dict[str, Any]):
        """
        3.8: Sincroniza el perfil con Google File Search.
        """
        from src.tools.google_file_search import file_search_tool

        try:
            content = json.dumps(profile, indent=2, ensure_ascii=False)
            await file_search_tool.upload_from_string(
                content=content,
                filename="user_profile.json",
                chat_id=chat_id,
                mime_type="application/json",
            )
            logger.info(f"Perfil sincronizado con Google Cloud para {chat_id}")
        except Exception as e:
            logger.warning(f"Error en sync_to_cloud para {chat_id}: {e}")

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


# Singleton (Stateless Manager)
user_profile_manager = UserProfileManager()
