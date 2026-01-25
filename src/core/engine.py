# src/core/engine.py
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI  # Added for OpenRouter support

from src.core.config import settings

logger = logging.getLogger(__name__)


# --- INICIO DE LA SOLUCIÓN CON OBSERVABILIDAD ---


# Crear instancia base del LLM con lógica de selección de proveedor
def _initialize_llm():
    if settings.LLM_PROVIDER == "openrouter":
        logger.info(
            f"Using OpenRouter Provider with model: {settings.OPENROUTER_MODEL_NAME}"
        )
        return ChatOpenAI(
            model=settings.OPENROUTER_MODEL_NAME,
            temperature=0.7,
            api_key=settings.OPENROUTER_API_KEY.get_secret_value()
            if settings.OPENROUTER_API_KEY
            else "dummy-key",
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        logger.info(f"Using Google Provider with model: {settings.DEFAULT_LLM_MODEL}")
        return ChatGoogleGenerativeAI(
            model=settings.DEFAULT_LLM_MODEL,
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            convert_system_message_to_human=True,
            api_key=settings.GOOGLE_API_KEY.get_secret_value()
            if settings.GOOGLE_API_KEY
            else None,
        )


llm = _initialize_llm()


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
