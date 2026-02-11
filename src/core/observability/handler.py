# src/core/observability/handler.py
"""
Callback handler para observabilidad LLM.
Responsabilidad única: Interceptar y trackear llamadas LLM.
"""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .correlation import get_correlation_id
from .metrics import LLMCallMetrics
from .prometheus_exporter import PrometheusLLMExporter

logger = logging.getLogger(__name__)


class LLMObservabilityHandler(BaseCallbackHandler):
    """
    Callback handler híbrido para observabilidad LLM.
    Combina LangSmith tracing con Prometheus metrics.
    """

    def __init__(self, call_type: str = "general"):
        """
        Inicializa el handler de observabilidad.

        Args:
            call_type: Tipo de llamada (routing, delegation, etc.)
        """
        super().__init__()
        self.call_type = call_type
        self.active_calls: dict[str, LLMCallMetrics] = {}
        self.exporter = PrometheusLLMExporter()

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Callback ejecutado al inicio de llamada LLM."""
        correlation_id = get_correlation_id()
        provider, model = self._extract_model_info(serialized)

        call_id = str(run_id)
        metrics = self._create_metrics(
            correlation_id, provider, model, call_id, prompts, kwargs
        )

        self.active_calls[call_id] = metrics
        self.exporter.update_active_calls_gauge(provider, model, increment=True)

        self._log_call_start(call_id, correlation_id, provider, model)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Callback ejecutado al finalizar llamada LLM exitosa."""
        # Aseguramos que 'response' no esté en kwargs para evitar duplicados
        kwargs.pop("response", None)
        self._finalize_call(run_id, response=response, success=True, **kwargs)

    def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt | BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Callback ejecutado cuando falla llamada LLM."""
        # Aseguramos que 'response' no esté en kwargs para evitar duplicados
        kwargs.pop("response", None)
        self._finalize_call(run_id, response=None, success=False, error=error, **kwargs)

    def _extract_model_info(self, serialized: dict[str, Any]) -> tuple[str, str]:
        """Extrae provider y modelo del LLM serializado."""
        provider = "unknown"
        model = "unknown"

        if serialized.get("id", [])[-1] == "ChatGoogleGenerativeAI":
            provider = "google"
            model = serialized.get("kwargs", {}).get("model", "gemini-pro")

        return provider, model

    def _create_metrics(
        self,
        correlation_id: str,
        provider: str,
        model: str,
        call_id: str,
        prompts: list[str],
        kwargs: dict[str, Any],
    ) -> LLMCallMetrics:
        """Crea objeto de métricas para una llamada LLM."""
        return LLMCallMetrics(
            correlation_id=correlation_id,
            provider=provider,
            model=model,
            call_type=self.call_type,
            start_time=time.time(),
            end_time=None,
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            success=True,
            error_message=None,
            estimated_cost_usd=None,
            metadata={"prompts_count": len(prompts), "call_id": call_id, **kwargs},
        )

    def _finalize_call(
        self,
        run_id: UUID,
        response: LLMResult | None,
        success: bool,
        error: Exception | KeyboardInterrupt | BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Finaliza y registra métricas de llamada LLM."""
        call_id = str(run_id)
        if call_id not in self.active_calls:
            logger.warning(f"Call ID {call_id} not found in active calls to finalize.")
            return
        metrics = self.active_calls[call_id]

        self._update_metrics_with_result(metrics, response, success, error)
        metrics.finalize()

        self.exporter.update_metrics(metrics)
        self.exporter.update_active_calls_gauge(
            metrics.provider, metrics.model, increment=False
        )

        del self.active_calls[call_id]
        self._log_call_completion(call_id, metrics, success)

    def _update_metrics_with_result(
        self,
        metrics: LLMCallMetrics,
        response: LLMResult | None,
        success: bool,
        error: BaseException | None = None,
    ) -> None:
        """Actualiza métricas con resultado de la llamada."""
        metrics.success = success
        if error:
            metrics.error_message = str(error)

        if response:
            # For LLMResult, extract usage from generations[0][0].message.usage_metadata
            if hasattr(response, "generations") and response.generations:
                first_gen = (
                    response.generations[0][0] if response.generations[0] else None
                )
                if (
                    first_gen
                    and hasattr(first_gen, "message")
                    and hasattr(first_gen.message, "usage_metadata")
                ):
                    if first_gen.message.usage_metadata:
                        self._extract_token_usage_from_metadata(
                            metrics, first_gen.message.usage_metadata
                        )
            # Try usage_metadata directly (newer LangChain AIMessage)
            elif hasattr(response, "usage_metadata") and response.usage_metadata:
                self._extract_token_usage_from_metadata(
                    metrics, response.usage_metadata
                )
            # Fallback to llm_output (older versions)
            elif response.llm_output:
                self._extract_token_usage(metrics, response.llm_output)

    def _extract_token_usage_from_metadata(
        self, metrics: LLMCallMetrics, usage_metadata: dict[str, Any]
    ) -> None:
        """Extrae información de tokens del usage_metadata (newer LangChain)."""
        metrics.input_tokens = usage_metadata.get("input_tokens")
        metrics.output_tokens = usage_metadata.get("output_tokens")

    def _extract_token_usage(
        self, metrics: LLMCallMetrics, llm_output: dict[str, Any]
    ) -> None:
        """Extrae información de tokens del response (legacy format)."""
        usage = llm_output.get("usage", {})
        metrics.input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        metrics.output_tokens = usage.get("completion_tokens") or usage.get(
            "output_tokens"
        )

    def _log_call_start(
        self, call_id: str, correlation_id: str, provider: str, model: str
    ) -> None:
        """Log inicio de llamada."""
        logger.debug(
            f"LLM call started: {call_id} | "
            f"correlation_id={correlation_id} | "
            f"provider={provider} | model={model} | type={self.call_type}"
        )

    def _log_call_completion(
        self, call_id: str, metrics: LLMCallMetrics, success: bool
    ) -> None:
        """Log finalización de llamada."""
        cost_str = (
            f"${metrics.estimated_cost_usd:.4f}"
            if metrics.estimated_cost_usd is not None
            else "$0.0000"
        )
        latency_str = (
            f"{metrics.latency_ms:.1f}ms" if metrics.latency_ms is not None else "N/A"
        )

        logger.info(
            f"LLM call completed: {call_id} | "
            f"correlation_id={metrics.correlation_id} | "
            f"success={success} | latency={latency_str} | "
            f"tokens={metrics.total_tokens} | cost={cost_str}"
        )
