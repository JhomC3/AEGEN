# src/core/registry.py
import logging
from typing import Protocol

from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


class Specialist(Protocol):
    """
    Una interfaz que define la estructura de un agente especialista.
    """

    @property
    def name(self) -> str:
        """El nombre único del especialista."""
        ...

    @property
    def graph(self) -> StateGraph:
        """El grafo de LangGraph que define la lógica del especialista."""
        ...

    @property
    def tool(self) -> BaseTool:
        """La herramienta que describe la capacidad del especialista para el enrutador."""
        ...


class SpecialistRegistry:
    """
    Un registro singleton para descubrir y gestionar agentes especialistas.
    """

    _instance = None
    _specialists: dict[str, Specialist] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._specialists = {}
        return cls._instance

    def register(self, specialist: Specialist):
        """Registra un nuevo especialista."""
        if specialist.name in self._specialists:
            logger.warning(
                f"Especialista '{specialist.name}' ya está registrado. Sobrescribiendo."
            )
        logger.info(f"Registrando especialista: '{specialist.name}'")
        self._specialists[specialist.name] = specialist

    def get_specialist(self, name: str) -> Specialist | None:
        """Obtiene un especialista por su nombre."""
        return self._specialists.get(name)

    def get_all_specialists(self) -> list[Specialist]:
        """Devuelve una lista de todos los especialistas registrados."""
        return list(self._specialists.values())

    def get_tools(self) -> list[BaseTool]:
        """Devuelve una lista de todas las herramientas de los especialistas."""
        return [s.tool for s in self._specialists.values()]


# Instancia única del registro para ser usada en toda la aplicación
specialist_registry = SpecialistRegistry()
