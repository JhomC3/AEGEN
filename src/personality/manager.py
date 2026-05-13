import logging
from typing import Optional

from src.personality.loader import PersonalityLoader
from src.personality.types import PersonalityBase, SkillOverlay

logger = logging.getLogger(__name__)


class PersonalityManager:
    """Singleton que gestiona la personalidad de MAGI."""

    _instance: Optional["PersonalityManager"] = None
    _base: PersonalityBase | None
    _overlays: dict[str, SkillOverlay]
    _loader: PersonalityLoader

    def __new__(cls, loader: PersonalityLoader | None = None) -> "PersonalityManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._base = None
            cls._instance._overlays = {}
            cls._instance._loader = loader or PersonalityLoader()
        return cls._instance

    def __init__(self, loader: PersonalityLoader | None = None) -> None:
        # __init__ se llama en cada llamada a PersonalityManager(),
        # pero el estado vive en la instancia compartida.
        if loader:
            self._loader = loader

    async def get_base(self) -> PersonalityBase:
        """Obtiene la personalidad base (con cache)."""
        if self._base is None:
            self._base = await self._loader.load_base()
        return self._base

    async def get_skill_overlay(self, skill_name: str) -> SkillOverlay | None:
        """Obtiene el overlay de un skill (con cache)."""
        if skill_name not in self._overlays:
            overlay = await self._loader.load_skill(skill_name)
            if overlay:
                self._overlays[skill_name] = overlay
        return self._overlays.get(skill_name)

    async def refresh(self) -> None:
        """Limpia el cache para forzar recarga de archivos."""
        self._base = None
        self._overlays = {}
        logger.info("Personalidad de MAGI recargada.")


# Singleton
personality_manager = PersonalityManager()
