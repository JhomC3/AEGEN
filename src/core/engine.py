# src/core/engine.py
"""
Fachada de observabilidad y diagnóstico de salud LLM.
Se conserva por compatibilidad con endpoints y controladores de FastAPI.
Las factorías de creación de LLM obsoletas han sido migradas al llm_registry.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def create_observable_config(
    call_type: str = "general", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Crea configuración con observabilidad automática de Prometheus."""
    from src.core.observability.handler import LLMObservabilityHandler

    if config is None:
        config = {}

    if "callbacks" not in config:
        config["callbacks"] = []

    # Validamos si ya está el handler en callbacks para no duplicar
    has_handler = any(
        isinstance(cb, LLMObservabilityHandler) for cb in config["callbacks"]
    )
    if not has_handler:
        observability_handler = LLMObservabilityHandler(call_type=call_type)
        config["callbacks"].append(observability_handler)

    return config


async def check_llm_health() -> dict[str, Any]:
    """Realiza una prueba de salud ligera al pool de chat del registry."""
    from src.core.llm_registry import get_llm

    start_time = time.time()
    try:
        # Ping ligero a través del canal chat_response (Gemini/Groq)
        chat_llm = get_llm("chat_response")
        response = await chat_llm.ainvoke("ping")
        latency_ms = (time.time() - start_time) * 1000

        # Obtener el contenido de respuesta del LLM (puede ser str o AIMessage)
        content = response.content if hasattr(response, "content") else str(response)

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "response_preview": str(content)[:50],
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("LLM Health Check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(latency_ms, 2),
        }
