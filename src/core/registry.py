# src/core/registry.py
import logging

from src.core.interfaces.workflow import IWorkflow

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """
    Un registro singleton para mapear nombres de tareas a clases de workflow.

    Utiliza el patrón de decorador para permitir que los workflows se registren
    automáticamente al ser importados por Python.
    """

    _instance = None
    _registry: dict[str, type[IWorkflow]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("WorkflowRegistry singleton created.")
        return cls._instance

    def register(self, task_name: str):
        """
        Decorador para registrar una clase de workflow.

        Args:
            task_name: El nombre único de la tarea que este workflow maneja.

        Returns:
            El decorador.
        """

        def decorator(cls: type[IWorkflow]):
            if not issubclass(cls, IWorkflow):
                raise TypeError(
                    f"Class {cls.__name__} must implement the IWorkflow interface."
                )
            if task_name in self._registry:
                logger.warning(
                    f"Workflow with task_name '{task_name}' is being overridden."
                )
            self._registry[task_name] = cls
            logger.info(f"Workflow '{cls.__name__}' registered for task '{task_name}'.")
            return cls

        return decorator

    def get_workflow(self, task_name: str) -> type[IWorkflow] | None:
        """

        Obtiene la clase de workflow para un nombre de tarea dado.

        Args:
            task_name: El nombre de la tarea.

        Returns:
            La clase del workflow o None si no se encuentra.
        """
        return self._registry.get(task_name)

    def get_all_workflows(self) -> dict[str, type[IWorkflow]]:
        """Devuelve una copia del registro completo."""
        return self._registry.copy()


# Instancia global del registro para ser usada en toda la aplicación
workflow_registry = WorkflowRegistry()
