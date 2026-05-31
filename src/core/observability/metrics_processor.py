# src/core/observability/metrics_processor.py
import logging
import time
from typing import Any

from langchain_core.outputs import LLMResult

from .metrics import LLMCallMetrics

logger = logging.getLogger(__name__)

_PROVIDER_BY_CLASS = {
    "ChatGoogleGenerativeAI": "google",
    "ChatGroq": "groq",
    "ChatAnthropic": "anthropic",
}

_OPENROUTER_DOMAINS = {"openrouter.ai"}
_AZURE_DOMAINS = {"openai.azure.com"}

_COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "groq": {"input": 0.0, "output": 0.0},
    "google": {"input": 0.000075, "output": 0.0003},
    "openrouter": {"input": 0.0, "output": 0.0},
    "openai": {"input": 0.0025, "output": 0.01},
    "anthropic": {"input": 0.003, "output": 0.015},
    "azure_openai": {"input": 0.0, "output": 0.0},
    "unknown": {"input": 0.0, "output": 0.0},
}


def extract_model_info(serialized: dict[str, Any]) -> tuple[str, str]:
    """Extrae provider y modelo del LLM serializado."""
    class_name = (serialized.get("id") or ["unknown"])[-1]
    kwargs = serialized.get("kwargs", {})

    if class_name in _PROVIDER_BY_CLASS:
        provider = _PROVIDER_BY_CLASS[class_name]
    elif class_name == "ChatOpenAI":
        base_url = str(kwargs.get("openai_api_base") or kwargs.get("base_url", ""))
        if any(domain in base_url for domain in _OPENROUTER_DOMAINS):
            provider = "openrouter"
        elif any(domain in base_url for domain in _AZURE_DOMAINS):
            provider = "azure_openai"
        else:
            provider = "openai"
    else:
        provider = "unknown"

    model = kwargs.get("model_name") or kwargs.get("model", "unknown")
    return provider, model


def estimate_cost_usd(
    provider: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float:
    """Estima el costo en USD basado en el provider y tokens consumidos."""
    costs = _COST_PER_1K_TOKENS.get(provider, _COST_PER_1K_TOKENS["unknown"])
    input_cost = ((input_tokens or 0) / 1000) * costs["input"]
    output_cost = ((output_tokens or 0) / 1000) * costs["output"]
    return round(input_cost + output_cost, 8)


def create_initial_metrics(
    correlation_id: str,
    provider: str,
    model: str,
    call_id: str,
    call_type: str,
    prompts_count: int,
    **kwargs: Any,
) -> LLMCallMetrics:
    """Crea objeto de métricas inicial para una llamada LLM."""
    return LLMCallMetrics(
        correlation_id=correlation_id,
        provider=provider,
        model=model,
        call_type=call_type,
        start_time=time.time(),
        end_time=None,
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        success=True,
        error_message=None,
        estimated_cost_usd=None,
        metadata={"prompts_count": prompts_count, "call_id": call_id, **kwargs},
    )


def update_metrics_from_result(
    metrics: LLMCallMetrics,
    response: LLMResult | None,
    success: bool,
    error: BaseException | None = None,
) -> None:
    """Actualiza metricas con resultado de la llamada."""
    metrics.success = success
    if error:
        metrics.error_message = str(error)

    if response:
        if hasattr(response, "generations") and response.generations:
            first_gen = response.generations[0][0] if response.generations[0] else None
            if first_gen and hasattr(first_gen, "message"):
                msg = first_gen.message
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    _extract_from_usage_metadata(metrics, msg.usage_metadata)
                    _update_cost(metrics)
                    return

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            _extract_from_usage_metadata(metrics, response.usage_metadata)
            _update_cost(metrics)
            return

        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("usage", {})
            metrics.input_tokens = usage.get("prompt_tokens") or usage.get(
                "input_tokens"
            )
            metrics.output_tokens = usage.get("completion_tokens") or usage.get(
                "output_tokens"
            )

    _update_cost(metrics)


def _update_cost(metrics: LLMCallMetrics) -> None:
    """Actualiza el costo estimado si hay tokens disponibles."""
    if metrics.input_tokens is not None or metrics.output_tokens is not None:
        metrics.estimated_cost_usd = estimate_cost_usd(
            metrics.provider,
            metrics.input_tokens,
            metrics.output_tokens,
        )


def _extract_from_usage_metadata(
    metrics: LLMCallMetrics, usage_metadata: dict[str, Any]
) -> None:
    """Helper para extraer de usage_metadata."""
    metrics.input_tokens = usage_metadata.get("input_tokens")
    metrics.output_tokens = usage_metadata.get("output_tokens")


def log_call_start(
    call_id: str, correlation_id: str, provider: str, model: str, call_type: str
) -> None:
    """Log inicio de llamada."""
    logger.debug(
        f"LLM call started: {call_id} | correlation_id={correlation_id} | "
        f"provider={provider} | model={model} | type={call_type}"
    )


def log_call_completion(call_id: str, metrics: LLMCallMetrics, success: bool) -> None:
    """Log finalización de llamada."""
    cost = metrics.estimated_cost_usd or 0.0
    latency = f"{metrics.latency_ms:.1f}ms" if metrics.latency_ms else "N/A"

    logger.info(
        f"LLM call completed: {call_id} | "
        f"correlation_id={metrics.correlation_id} | success={success} | "
        f"latency={latency} | tokens={metrics.total_tokens} | cost=${cost:.4f}"
    )
