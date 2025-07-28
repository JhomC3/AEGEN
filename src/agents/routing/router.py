import logging
from typing import Any, Dict

from agents.workflows.base_workflow import IWorkflow

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Enrutador de agentes que decide qué workflow ejecutar basándose en los
    datos de entrada.
    """

    def __init__(self, workflows: Dict[str, IWorkflow]):
        """
        Inicializa el enrutador con un registro de workflows disponibles.

        Args:
            workflows: Un diccionario donde las claves son identificadores de tareas
                       y los valores son instancias de workflows que implementan
                       la interfaz IWorkflow.
        """
        self._workflows = workflows
        logger.info(
            f"AgentRouter initialized with workflows: {list(self._workflows.keys())}"
        )

    async def route_task(self, data: Dict[str, Any]) -> None:
        """
        Analiza los datos de entrada y ejecuta el workflow apropiado.

        Esta es la implementación inicial basada en reglas. En el futuro,
        podría ser reemplazada por una llamada a un LLM para una decisión
        más inteligente.

        Args:
            data: Los datos procesados por un message handler.
        """
        # --- Lógica de Enrutamiento (Inicialmente basada en reglas) ---

        # Regla 1: Si el mensaje es de cualquier tipo, ejecutar el workflow de Excel.
        # Esta es la implementación para la tarea actual.
        if "export_to_excel" in self._workflows:
            logger.info("Routing task to 'export_to_excel' workflow.")
            try:
                # No esperamos a que termine para no bloquear la respuesta a Telegram
                # asyncio.create_task(self._workflows["export_to_excel"].run(data))

                # Para la depuración inicial, podemos esperarlo:
                result = await self._workflows["export_to_excel"].run(data)
                logger.info(
                    f"Workflow 'export_to_excel' finished with result: {result}"
                )

            except Exception as e:
                logger.error(
                    f"Error executing 'export_to_excel' workflow: {e}", exc_info=True
                )

        # Aquí se podrían añadir más reglas en el futuro:
        # if data.get("type") == "text" and "pregunta" in data.get("content", "").lower():
        #     logger.info("Routing task to 'qa_workflow'.")
        #     asyncio.create_task(self._workflows["qa_workflow"].run(data))

        else:
            logger.info("No specific workflow rule matched. No action taken.")
