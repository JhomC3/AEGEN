from abc import ABC, abstractmethod
from typing import Any


class IWorkflow(ABC):
    """
    Interfaz abstracta para todos los workflows (flujos de trabajo) de agentes.

    Define un contrato estándar para la ejecución de tareas complejas.
    Cualquier agente que represente un proceso de negocio o una tarea de varios
    pasos debe implementar esta interfaz.
    """

    @abstractmethod
    async def run(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta el workflow.

        Args:
            data: Un diccionario que contiene los datos necesarios para que
                  el workflow se ejecute. Puede ser el output de un
                  message handler o de otro workflow.

        Returns:
            Un diccionario con los resultados de la ejecución del workflow.
            La estructura de este diccionario dependerá de cada implementación.
        """
        pass
