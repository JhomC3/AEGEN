# src/core/engine.py
import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)

# Lista de proveedores en orden de prioridad para fallback
PROVIDER_PRIORITY = ["groq", "google", "openrouter"]


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


def _create_groq_llm():
    """Crea instancia de Groq."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as e:
        raise ImportError(
            "langchain-groq no está instalado. Ejecuta: pip install langchain-groq"
        ) from e

    logger.info(f"Initializing Groq with model: {settings.GROQ_MODEL_NAME}")
    api_key = None
    if settings.GROQ_API_KEY:
        api_key = settings.GROQ_API_KEY.get_secret_value()

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    return ChatGroq(
        model=settings.GROQ_MODEL_NAME,
        temperature=0.7,
        api_key=api_key,
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


def _get_provider_factory(provider: str):
    """Retorna la función factory para el proveedor especificado."""
    factories = {
        "openrouter": _create_openrouter_llm,
        "groq": _create_groq_llm,
        "google": _create_google_llm,
    }
    return factories.get(provider)


def _initialize_llm():
    """
    Inicializa el LLM con fallback automático entre proveedores.
    Orden de fallback: groq → google → openrouter
    """
    primary = settings.LLM_PROVIDER
    logger.info(f"[LLM] Initializing. Primary provider: {primary}")

    # Construir lista de proveedores a intentar (primario primero, luego fallbacks)
    providers_to_try = [primary]
    for p in PROVIDER_PRIORITY:
        if p not in providers_to_try:
            providers_to_try.append(p)

    last_error = None
    for provider in providers_to_try:
        factory = _get_provider_factory(provider)
        if not factory:
            logger.warning(f"[LLM] Unknown provider: {provider}, skipping")
            continue

        try:
            llm_instance = factory()
            logger.info(f"[LLM] Successfully initialized with provider: {provider}")
            return llm_instance
        except Exception as e:
            last_error = e
            logger.warning(f"[LLM] Failed to initialize {provider}: {e}")
            continue

    # Si todos fallan, lanzar el último error
    logger.critical("[LLM] All providers failed to initialize!")
    # Retornar Google como último recurso desesperado para evitar crash total
    try:
        return _create_google_llm()
    except Exception:
        raise RuntimeError(
            f"Could not initialize any LLM provider. Last error: {last_error}"
        ) from last_error


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
    Realiza una prueba de salud del LLM actual con medición de latencia.
    """
    import time

    model_name = {
        "openrouter": settings.OPENROUTER_MODEL_NAME,
        "groq": settings.GROQ_MODEL_NAME,
        "google": settings.DEFAULT_LLM_MODEL,
    }.get(settings.LLM_PROVIDER, "unknown")

    start_time = time.time()
    try:
        response = await llm.ainvoke("ping")
        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "provider": settings.LLM_PROVIDER,
            "model": model_name,
            "latency_ms": round(latency_ms, 2),
            "response_preview": str(response.content)[:50],
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"LLM Health Check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "provider": settings.LLM_PROVIDER,
            "model": model_name,
            "latency_ms": round(latency_ms, 2),
        }


logger.info(
    f"[LLM] Engine ready. Provider: {settings.LLM_PROVIDER} | "
    f"Model: {settings.GROQ_MODEL_NAME if settings.LLM_PROVIDER == 'groq' else (settings.OPENROUTER_MODEL_NAME if settings.LLM_PROVIDER == 'openrouter' else settings.DEFAULT_LLM_MODEL)}"
)
