# src/agents/orchestrator.py
import logging

from src.core.registry import workflow_registry

logger = logging.getLogger(__name__)


class WorkflowCoordinator:
    """
    Actúa como el principal consumidor de eventos del bus.
    Su función es orquestar la ejecución de workflows basados en los
    eventos que recibe.
    """

    def __init__(self):
        logger.info("WorkflowCoordinator instance created.")
        # En el futuro, podría tener dependencias como un cliente de DB para idempotencia.

    async def handle_workflow_event(self, event: dict) -> None:
        """
        Manejador de eventos para el topic principal de tareas.

        Este método es suscrito al IEventBus.
        """
        task_id = event.get("task_id")
        task_name = event.get("task_name")
        logger.info(f"[TaskID: {task_id}] Received event for task '{task_name}'.")

        if not task_name:
            logger.error(
                f"[TaskID: {task_id}] Event is missing 'task_name'. Discarding."
            )
            return

        workflow_class = workflow_registry.get_workflow(task_name)

        if not workflow_class:
            logger.error(
                f"[TaskID: {task_id}] No workflow registered for task_name '{task_name}'. Discarding."
            )
            return

        try:
            # Instanciar y ejecutar el workflow
            workflow_instance = workflow_class()
            logger.debug(
                f"[TaskID: {task_id}] Executing workflow: {workflow_class.__name__}"
            )
            await workflow_instance.execute(event)
            logger.info(
                f"[TaskID: {task_id}] Workflow {workflow_class.__name__} executed successfully."
            )
        except Exception:
            logger.exception(
                f"[TaskID: {task_id}] An unexpected error occurred while executing workflow {workflow_class.__name__}."
            )
            # Aquí se podría implementar lógica de reintentos o DLQ en Fase 2.
