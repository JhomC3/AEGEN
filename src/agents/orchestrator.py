# src/agents/orchestrator.py
import logging

from src.core.registry import workflow_registry
from src.core.resilience import retry_on_failure

logger = logging.getLogger(__name__)


class WorkflowCoordinator:
    """
    Actúa como el principal consumidor de eventos del bus.
    Su función es orquestar la ejecución de workflows basados en los
    eventos que recibe.
    """

    def __init__(self):
        logger.info("WorkflowCoordinator instance created.")
        # Para la Fase 1, usamos un set en memoria para la idempotencia.
        # En Fase 2, esto sería reemplazado por un sistema persistente (ej. Redis).
        self.processed_tasks: set[str] = set()

    async def handle_workflow_event(self, event: dict) -> None:
        """
        Manejador de eventos para el topic principal de tareas.

        Este método es suscrito al IEventBus.
        """
        task_id = event.get("task_id")
        task_name = event.get("task_name")
        logger.info(f"[TaskID: {task_id}] Received event for task '{task_name}'.")

        if not task_id:
            logger.error("Event is missing 'task_id'. Discarding.")
            return

        # --- Idempotencia ---
        if task_id in self.processed_tasks:
            logger.warning(
                f"[TaskID: {task_id}] Task already processed. Ignoring duplicate event."
            )
            return

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
            # Marcar como procesado ANTES de la ejecución
            self.processed_tasks.add(task_id)

            # Instanciar el workflow
            workflow_instance = workflow_class()
            logger.debug(
                f"[TaskID: {task_id}] Preparing to execute workflow: {workflow_class.__name__}"
            )

            # Aplicar el decorador de reintentos dinámicamente
            resilient_executor = retry_on_failure(retries=3, delay=1, backoff=2)
            decorated_execute = resilient_executor(workflow_instance.execute)

            # Ejecutar la versión decorada del método
            await decorated_execute(event)

            logger.info(
                f"[TaskID: {task_id}] Workflow {workflow_class.__name__} executed successfully."
            )
        except Exception:
            # El decorador ya ha logueado los reintentos. Este log captura el fallo final.
            logger.exception(
                f"[TaskID: {task_id}] Workflow {workflow_class.__name__} failed definitively after all retries."
            )
            # Si falla definitivamente, podríamos querer eliminarlo del set para permitir un reintento manual futuro.
            # Por ahora, lo dejamos para garantizar la no repetición.
            # En Fase 2, esto se gestionaría con una DLQ.
