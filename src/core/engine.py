# src/core/engine.py
import logging
from typing import Any

import psutil
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.config import settings
from src.core.schemas import SystemState, SystemStatus

logger = logging.getLogger(__name__)


# --- INICIO DE LA SOLUCIÓN CON OBSERVABILIDAD ---

# Crear instancia base del LLM
llm = ChatGoogleGenerativeAI(
    model=settings.DEFAULT_LLM_MODEL,
    temperature=settings.DEFAULT_TEMPERATURE,
    convert_system_message_to_human=True,  # Necesario para algunos modelos de Google
    google_api_key=settings.GOOGLE_API_KEY.get_secret_value() if settings.GOOGLE_API_KEY else None,
)


def create_observable_config(
    call_type: str = "general", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Crea configuración con observabilidad automática.

    Args:
        call_type: Tipo de llamada para métricas
        config: Configuración base existente

    Returns:
        Configuración con handler de observabilidad
    """
    from src.core.observability.handler import LLMObservabilityHandler

    if config is None:
        config = {}

    if "callbacks" not in config:
        config["callbacks"] = []

    # Agregar handler de observabilidad
    observability_handler = LLMObservabilityHandler(call_type=call_type)
    config["callbacks"].append(observability_handler)

    return config


logger.info(
    f"LLM Engine initialized with observability support: {settings.DEFAULT_LLM_MODEL}"
)

# --- FIN DE LA SOLUCIÓN CON OBSERVABILIDAD ---


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
