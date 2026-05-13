# src/core/registry.py
import logging
from typing import Any, cast

from langchain_core.tools import BaseTool

from src.core.interfaces.specialist import SpecialistInterface

logger = logging.getLogger(__name__)


class SpecialistRegistry:
    """
    Un registro singleton para descubrir y gestionar agentes especialistas.
    Soporta registro individual o masivo desde Skills cargados.
    """

    _instance: Any = None
    _specialists: dict[str, SpecialistInterface] = {}

    def __new__(cls) -> "SpecialistRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._specialists = {}
        return cast("SpecialistRegistry", cls._instance)

    def register(self, specialist: SpecialistInterface) -> None:
        """Registra un nuevo especialista."""
        if specialist.name in self._specialists:
            logger.warning(
                "Especialista '%s' ya registrado. Sobrescribiendo.", specialist.name
            )
        logger.info("Registrando especialista: '%s'", specialist.name)
        self._specialists[specialist.name] = specialist

    def register_from_loaded_skills(self, skills: list[Any]) -> None:
        """
        Registra especialistas generados a partir de una lista de LoadedSkill.
        Evita circular imports importando SkillBasedSpecialist aquí.
        """
        from src.agents.specialists.skill_based_specialist import SkillBasedSpecialist

        for loaded_skill in skills:
            try:
                specialist = SkillBasedSpecialist(loaded_skill)
                self.register(specialist)
            except Exception:
                logger.exception(
                    "Error registrando skill como especialista: %s",
                    loaded_skill.content.manifest.id,
                )

    def get_specialist(self, name: str) -> SpecialistInterface | None:
        """Obtiene un especialista por su nombre."""
        return self._specialists.get(name)

    def get_all_specialists(self) -> list[SpecialistInterface]:
        """Devuelve una lista de todos los especialistas registrados."""
        return list(self._specialists.values())

    def get_tools(self) -> list[BaseTool]:
        """Devuelve una lista de todas las herramientas de los especialistas."""
        # Filtrar solo aquellos que tienen tool (algunos skills podrían no tenerlo)
        return [s.tool for s in self._specialists.values() if s.tool is not None]


# Instancia única del registro para ser usada en toda la aplicación
specialist_registry = SpecialistRegistry()
