# src/core/engine.py
import logging
import time
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


def _create_groq_llm(model_name: str | None = None) -> Any:
    """Crea instancia de Groq con reintentos agresivos."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as e:
        raise ImportError(
            "langchain-groq no está instalado. Ejecuta: pip install langchain-groq"
        ) from e

    target_model = model_name or settings.GROQ_MODEL_NAME
    logger.info("Initializing Groq with model: %s", target_model)
    api_key = settings.GROQ_API_KEY

    return ChatGroq(
        model=target_model,
        temperature=0.7,
        api_key=api_key,
        max_retries=3,
        timeout=60,
    )


def _create_google_llm(model_name: str | None = None) -> Any:
    """Crea instancia de Google Gemini."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    raw_model = model_name or settings.RAG_MODEL
    target_model = (
        raw_model if raw_model.startswith("models/") else f"models/{raw_model}"
    )

    logger.info("Initializing Google Provider with model: %s", target_model)

    return ChatGoogleGenerativeAI(
        model=target_model,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        convert_system_message_to_human=True,
        api_key=settings.GOOGLE_API_KEY,
    )


def get_fast_llm() -> Any:
    """
    Motor optimizado para velocidad (Ruteo y Chat General).
    Primario: Groq (gpt-oss-120b) → Fallback: Gemini (gemini-2.5-flash-lite)
    """
    primary = _create_groq_llm(settings.CHAT_MODEL)
    fallback_groq = _create_groq_llm(settings.GROQ_BACKUP_MODEL_NAME)
    fallback_gemini = _create_google_llm(settings.RAG_MODEL)

    return primary.with_fallbacks([fallback_groq, fallback_gemini])


def get_analytical_llm() -> Any:
    """
    Motor optimizado para razonamiento (TCC, Análisis, Consolidación).
    Primario: Groq (gpt-oss-120b) → Fallback: Gemini (gemini-2.5-flash-lite)
    """
    primary = _create_groq_llm(settings.CHAT_MODEL)
    fallback = _create_google_llm(settings.RAG_MODEL)

    return primary.with_fallbacks([fallback])


def get_rag_llm() -> Any:
    """Motor optimizado para contexto largo (Gemini)."""
    return _create_google_llm()


# Mantener 'llm' global por compatibilidad legacy, apuntando al rápido por defecto
llm = get_fast_llm()


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
    """Realiza una prueba de salud de los motores LLM."""
    start_time = time.time()
    try:
        # Probar el motor rápido (Groq)
        response = await llm.ainvoke("ping")
        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "response_preview": str(response.content)[:50],
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("LLM Health Check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(latency_ms, 2),
        }


logger.info("[LLM] Engine ready: Groq primary → Gemini fallback (OpenRouter removed)")
