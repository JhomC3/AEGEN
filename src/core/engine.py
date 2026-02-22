# src/core/engine.py
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


def _create_openrouter_llm(timeout: int = 30) -> Any:
    """Crea instancia de OpenRouter con reintentos."""
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL_NAME,
        temperature=0.7,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        max_retries=2,
        timeout=timeout,
    )


def _create_groq_llm(
    model_name: str | None = None,
    timeout: int = 10,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> Any:
    """Crea instancia de Groq con configuración específica."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as e:
        raise ImportError("langchain-groq no está instalado.") from e

    target_model = model_name or settings.CHAT_MODEL
    api_key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else None

    kwargs = {}
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

    return ChatGroq(
        model=target_model,
        temperature=temperature,
        api_key=api_key,
        max_retries=2,
        timeout=timeout,
        **kwargs,
    )


def _create_google_llm(model_name: str | None = None, timeout: int = 15) -> Any:
    """Crea instancia de Google Gemini."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    target_model = model_name or settings.RAG_MODEL
    return ChatGoogleGenerativeAI(
        model=target_model,
        temperature=0.3,
        top_p=0.9,
        convert_system_message_to_human=True,
        api_key=settings.GOOGLE_API_KEY,
        timeout=timeout,
    )


def _initialize_chat_engine() -> Any:
    """Motor especializado en conversación empática."""
    logger.info("[LLM] Initializing MAGI-CHAT Engine")
    primary = _create_groq_llm(settings.CHAT_MODEL, timeout=10, temperature=0.7)
    fallback = _create_google_llm(settings.CHAT_FALLBACK_MODEL, timeout=15)
    return primary.with_fallbacks([fallback])


def _initialize_core_engine() -> Any:
    """Motor especializado en tareas estructurales (JSON)."""
    logger.info("[LLM] Initializing MAGI-CORE Engine (Structured)")
    primary = _create_groq_llm(
        settings.CORE_MODEL, timeout=15, temperature=0, json_mode=True
    )
    fallback = _create_google_llm(settings.RAG_MODEL, timeout=20)
    return primary.with_fallbacks([fallback])


# Motores Duales
llm_chat = _initialize_chat_engine()
llm_core = _initialize_core_engine()

# Legacy Alias
llm = llm_chat


def create_observable_config(
    call_type: str = "general", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Crea configuración con observabilidad automática."""
    from src.core.observability.handler import LLMObservabilityHandler

    if config is None:
        config = {}
    if "callbacks" not in config:
        config["callbacks"] = []

    config["callbacks"].append(LLMObservabilityHandler(call_type=call_type))
    return config


async def check_llm_health() -> dict[str, Any]:
    """Prueba de salud de los motores."""
    import time

    results = {}
    for name, engine in [("chat", llm_chat), ("core", llm_core)]:
        start = time.time()
        try:
            await engine.ainvoke("ping")
            results[name] = {
                "status": "healthy",
                "latency": round((time.time() - start) * 1000, 2),
            }
        except Exception as e:
            results[name] = {"status": "unhealthy", "error": str(e)}
    return results


logger.info("[LLM] Engines ready: Dual Brain Strategy Active.")
