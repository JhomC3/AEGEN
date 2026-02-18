# src/core/engine.py
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


def _create_openrouter_llm() -> Any:
    """Crea instancia de OpenRouter con reintentos."""
    logger.info(
        "Initializing OpenRouter with model: %s", settings.OPENROUTER_MODEL_NAME
    )

    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL_NAME,
        temperature=0.7,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        max_retries=3,
        timeout=60,
    )


def _create_groq_llm(model_name: str | None = None) -> Any:
    """Crea instancia de Groq con reintentos agresivos."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as e:
        raise ImportError(
            "langchain-groq no está instalado. Ejecuta: pip install langchain-groq"
        ) from e

    target_model = model_name or settings.GROQ_MODEL_NAME
    logger.info(f"Initializing Groq with model: {target_model}")
    api_key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else None

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

    target_model = model_name or settings.RAG_MODEL
    logger.info(f"Initializing Google Provider with model: {target_model}")

    return ChatGoogleGenerativeAI(
        model=target_model,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        convert_system_message_to_human=True,
        api_key=settings.GOOGLE_API_KEY,
    )


def _initialize_llm() -> Any:
    """
    Inicializa el LLM con una estrategia robusta de reintentos y fallbacks multinivel.
    Jerarquía:
    1. Groq Principal (Moonshot)
    2. Groq Backup (gpt-oss-120)
    3. Google Gemini
    4. OpenRouter (Último recurso)
    """
    logger.info("[LLM] Building Resilient Engine with Multi-Level Fallback")

    try:
        # Nivel 1: Chat Principal (e.g. Kimi K2 via Groq)
        primary_chat = _create_groq_llm(settings.CHAT_MODEL)

        # Nivel 2: Groq Backup
        groq_backup = _create_groq_llm(settings.CHAT_FALLBACK_MODEL)

        # Nivel 3: Google (Mantenemos gemini-2.5-flash-lite via RAG_MODEL o DEFAULT)
        google_backup = _create_google_llm()

        # Nivel 4: OpenRouter
        openrouter_last_resort = _create_openrouter_llm()

        # Construir la cadena de fallbacks en orden estricto
        resilient_llm = primary_chat.with_fallbacks([
            groq_backup,
            google_backup,
            openrouter_last_resort,
        ])

        logger.info(
            "[LLM] Resilient chain created: Groq(Primary) -> "
            "Groq(Backup) -> Google -> OpenRouter"
        )
        return resilient_llm

    except Exception as e:
        logger.critical(f"[LLM] Error building resilient engine: {e}")
        try:
            return _create_google_llm()
        except Exception:
            raise RuntimeError(
                f"Total failure in LLM engine initialization: {e}"
            ) from e


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

    start_time = time.time()
    try:
        response = await llm.ainvoke("ping")
        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "response_preview": str(response.content)[:50],
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"LLM Health Check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(latency_ms, 2),
        }


logger.info("[LLM] Engine ready with Multi-Level Fallback configured.")
