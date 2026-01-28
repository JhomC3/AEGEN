# src/core/engine.py
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


def _create_openrouter_llm():
    """Crea instancia de OpenRouter."""
    logger.info(f"Initializing OpenRouter with model: {settings.OPENROUTER_MODEL_NAME}")
    api_key = None
    if settings.OPENROUTER_API_KEY:
        api_key = settings.OPENROUTER_API_KEY.get_secret_value()

    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL_NAME,
        temperature=0.7,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _create_google_llm():
    """Crea instancia de Google Gemini."""
    logger.info(
        f"Initializing Google Provider with model: {settings.DEFAULT_LLM_MODEL}"
    )

    api_key = None
    if settings.GOOGLE_API_KEY:
        api_key = settings.GOOGLE_API_KEY.get_secret_value()

    return ChatGoogleGenerativeAI(
        model=settings.DEFAULT_LLM_MODEL,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        convert_system_message_to_human=True,
        api_key=api_key,
    )


def _initialize_llm():
    """
    Inicializa el LLM principal con lógica de fallback.
    Si el proveedor preferido falla, intenta con el alternativo.
    """
    primary_provider = settings.LLM_PROVIDER

    try:
        if primary_provider == "openrouter":
            return _create_openrouter_llm()
        else:
            return _create_google_llm()
    except Exception as e:
        logger.error(
            f"Failed to initialize primary LLM provider '{primary_provider}': {e}"
        )

        # Fallback Logic
        fallback_provider = (
            "google" if primary_provider == "openrouter" else "openrouter"
        )
        logger.warning(f"Attempting fallback to provider: {fallback_provider}")

        try:
            if fallback_provider == "google":
                return _create_google_llm()
            else:
                return _create_openrouter_llm()
        except Exception as fe:
            logger.critical(f"Critical Error: Both LLM providers failed. {fe}")
            # Retornamos el de Google por defecto para evitar crashes inmediatos
            return _create_google_llm()


# Instancia singleton del LLM
llm = _initialize_llm()


def create_observable_config(
    call_type: str = "general", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Crea configuración con observabilidad automática."""
    from src.core.observability.handler import LLMObservabilityHandler

    if config is None:
        config = {}

    if "callbacks" not in config:
        config["callbacks"] = []

    observability_handler = LLMObservabilityHandler(call_type=call_type)
    config["callbacks"].append(observability_handler)

    return config


async def check_llm_health() -> dict[str, Any]:
    """
    Realiza una prueba de salud del LLM actual.
    """
    try:
        response = await llm.ainvoke("ping")
        return {
            "status": "healthy",
            "provider": settings.LLM_PROVIDER,
            "model": settings.OPENROUTER_MODEL_NAME
            if settings.LLM_PROVIDER == "openrouter"
            else settings.DEFAULT_LLM_MODEL,
            "response_preview": str(response.content)[:20],
        }
    except Exception as e:
        logger.error(f"LLM Health Check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "provider": settings.LLM_PROVIDER,
        }


logger.info(
    f"LLM Engine initialized. Primary: {settings.LLM_PROVIDER} | Model: {settings.OPENROUTER_MODEL_NAME if settings.LLM_PROVIDER == 'openrouter' else settings.DEFAULT_LLM_MODEL}"
)
