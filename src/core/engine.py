# src/core/engine.py
import logging

import psutil
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.config import settings
from src.core.schemas import SystemState, SystemStatus

logger = logging.getLogger(__name__)


# --- INICIO DE LA SOLUCIÓN ---

# Crear una única instancia del LLM para ser usada en toda la aplicación.
# Se carga la configuración desde el objeto `settings` centralizado.
# La API key se carga automáticamente desde la variable de entorno GOOGLE_API_KEY.
llm = ChatGoogleGenerativeAI(
    model=settings.DEFAULT_LLM_MODEL,
    temperature=settings.DEFAULT_TEMPERATURE,
    convert_system_message_to_human=True,  # Necesario para algunos modelos de Google
)

logger.info(f"LLM Engine initialized with model: {settings.DEFAULT_LLM_MODEL}")

# --- FIN DE LA SOLUCIÓN ---


class MigrationDecisionEngine:
    """
    Motor para decidir si el sistema debe migrar a una arquitectura distribuida.
    """

    def __init__(self):
        self.cpu_threshold = settings.CPU_THRESHOLD_PERCENT
        self.mem_threshold = settings.MEMORY_THRESHOLD_PERCENT
        logger.info(
            f"MigrationDecisionEngine initialized with CPU threshold: {self.cpu_threshold}% "
            f"and Memory threshold: {self.mem_threshold}%"
        )

    def get_system_status(self) -> SystemStatus:
        """
        Evalúa el estado actual del sistema y recomienda una acción.

        Returns:
            Un objeto SystemStatus con las métricas y la recomendación.
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        mem_percent = psutil.virtual_memory().percent

        if cpu_percent > self.cpu_threshold or mem_percent > self.mem_threshold:
            state = SystemState.MIGRATE_TO_DISTRIBUTED
            message = (
                f"System resource usage is high (CPU: {cpu_percent}%, Memory: {mem_percent}%). "
                "Migration to a distributed architecture is recommended."
            )
            logger.warning(message)
        else:
            state = SystemState.STAY_LOCAL
            message = (
                f"System resource usage is normal (CPU: {cpu_percent}%, Memory: {mem_percent}%). "
                "Staying with local architecture."
            )
            logger.info(message)

        return SystemStatus(
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=mem_percent,
            state=state,
            message=message,
        )
