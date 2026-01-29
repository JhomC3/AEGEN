import logging

from src.personality.loader import PersonalityLoader
from src.personality.types import PersonalityBase, SkillOverlay

logger = logging.getLogger(__name__)


class PersonalityManager:
    """Singleton que gestiona la personalidad de MAGI."""

    _instance = None
    _base: PersonalityBase | None = None
    _overlays: dict[str, SkillOverlay] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._loader = PersonalityLoader()
        return cls._instance

    async def get_base(self) -> PersonalityBase:
        """Obtiene la personalidad base (con cache)."""
        if self._base is None:
            self._base = await self._loader.load_base()
        return self._base

    async def get_skill_overlay(self, skill_name: str) -> SkillOverlay | None:
        """Obtiene el overlay de un skill (con cache)."""
        if skill_name not in self._overlays:
            overlay = await self._loader.load_skill_overlay(skill_name)
            if overlay:
                self._overlays[skill_name] = overlay
        return self._overlays.get(skill_name)

    async def refresh(self):
        """Limpia el cache para forzar recarga de archivos."""
        self._base = None
        self._overlays = {}
        logger.info("Personalidad de MAGI recargada.")


# Singleton
personality_manager = PersonalityManager()
