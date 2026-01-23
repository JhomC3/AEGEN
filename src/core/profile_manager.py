import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

logger = logging.getLogger(__name__)

# Rutas - Relativas al root del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "memory"
PROFILE_PATH = STORAGE_DIR / "user_profile.json"


class UserProfileManager:
    """
    Gestiona el perfil evolutivo del usuario.
    Versión Rescue MAGI (v0.3.2): Prioriza estados psicológicos discretos sobre métricas decimales.
    """

    def __init__(self):
        self.profile: dict[str, Any] = self._get_default_profile()
        self._ensure_storage()

    def _ensure_storage(self):
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_default_profile(self) -> dict[str, Any]:
        """Estructura simplificada para dirección clara del LLM."""
        return {
            "identity": {"name": "Usuario", "style": "Deep Existential Stoic"},
            "psychological_state": {
                "current_phase": "Strategic Resignation",  # Estado inicial según feedback
                "key_metaphors": [
                    "The Bus (Integration)",
                    "Robot Mode (Functionality)",
                    "The Forge",
                ],
                "active_struggles": ["Apathy", "Sadness", "Meaning Crisis"],
            },
            "evolution": {"level": 1, "milestones_count": 0},
            "active_tags": ["bienvenida", "resiliencia"],
            "timeline": [
                {
                    "date": datetime.now().isoformat(),
                    "event": "Reinicio de Perfil - Rescue MAGI v0.3.2",
                    "type": "system",
                }
            ],
            "metadata": {
                "version": "0.3.2",
                "last_updated": datetime.now().isoformat(),
            },
        }

    async def load_profile(self) -> dict[str, Any]:
        if not PROFILE_PATH.exists():
            logger.info("Perfil no encontrado. Creando Value Profile v0.3.2.")
            await self.save_profile()
            return self.profile

        try:
            async with aiofiles.open(PROFILE_PATH, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                # Migración simple si es versión vieja
                if data.get("metrics") and not data.get("psychological_state"):
                    logger.info("Migrando perfil legacy a v0.3.2")
                    migrated = self._get_default_profile()
                    migrated["timeline"] = data.get("timeline", [])
                    self.profile = migrated
                    await self.save_profile()
                    return self.profile

                self.profile = data
                return self.profile
        except Exception as e:
            logger.error(f"Error cargando perfil: {e}")
            return self.profile

    async def save_profile(self):
        try:
            self.profile["metadata"]["last_updated"] = datetime.now().isoformat()
            async with aiofiles.open(PROFILE_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.profile, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Error guardando perfil: {e}")

    async def add_milestone(self, event: str):
        """Registra un hito importante."""
        self.profile["timeline"].append({
            "date": datetime.now().isoformat(),
            "event": event,
            "type": "milestone",
        })
        self.profile["evolution"]["milestones_count"] += 1
        await self.save_profile()

    def get_context_for_prompt(self) -> dict[str, str]:
        """Retorna contexto formateado para inyectar en el prompt."""
        psy = self.profile.get("psychological_state", {})
        metaphors = ", ".join(psy.get("key_metaphors", []))
        struggles = ", ".join(psy.get("active_struggles", []))
        return {
            "phase": psy.get("current_phase", "Unknown"),
            "metaphors": metaphors,
            "struggles": struggles,
        }

    def get_active_tags(self) -> list[str]:
        return self.profile.get("active_tags", [])

    def get_style(self) -> str:
        return self.profile.get("identity", {}).get("style", "Deep Existential Stoic")


# Singleton
user_profile_manager = UserProfileManager()
