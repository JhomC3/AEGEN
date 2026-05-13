"""Interfaz para trabajadores asíncronos de skills."""

from abc import ABC, abstractmethod
from typing import Any

from src.core.schemas.common import AgentResultStatus


class ISkillWorker(ABC):
    """
    Define el contrato para una tarea que se ejecuta en segundo plano.
    """

    @abstractmethod
    async def execute(self, task_id: str, context: dict[str, Any]) -> Any:
        """Ejecuta la lógica de la tarea."""
        pass

    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """Cancela una tarea en ejecución."""
        pass

    @abstractmethod
    async def get_status(self, task_id: str) -> AgentResultStatus:
        """Obtiene el estado actual de la tarea."""
        pass
