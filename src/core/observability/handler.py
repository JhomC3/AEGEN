# src/core/observability/handler.py
"""
Callback handler para observabilidad LLM.
Responsabilidad única: Interceptar y trackear llamadas LLM.
"""

import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .correlation import get_correlation_id
from .metrics import LLMCallMetrics
from .metrics_processor import (
    create_initial_metrics,
    extract_model_info,
    log_call_completion,
    log_call_start,
    update_metrics_from_result,
)
from .prometheus_exporter import PrometheusLLMExporter

logger = logging.getLogger(__name__)


class LLMObservabilityHandler(BaseCallbackHandler):
    """
    Callback handler híbrido para observabilidad LLM.
    """

    def __init__(self, call_type: str = "general") -> None:
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
        provider, model = extract_model_info(serialized)

        call_id = str(run_id)
        metrics = create_initial_metrics(
            correlation_id,
            provider,
            model,
            call_id,
            self.call_type,
            len(prompts),
            **kwargs,
        )

        self.active_calls[call_id] = metrics
        self.exporter.update_active_calls_gauge(provider, model, increment=True)

        log_call_start(call_id, correlation_id, provider, model, self.call_type)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Callback ejecutado al finalizar llamada LLM exitosa."""
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
        kwargs.pop("response", None)
        self._finalize_call(run_id, response=None, success=False, error=error, **kwargs)

    def _finalize_call(
        self,
        run_id: UUID,
        response: LLMResult | None,
        success: bool,
        error: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Finaliza y registra métricas de llamada LLM."""
        call_id = str(run_id)
        if call_id not in self.active_calls:
            logger.warning(f"Call ID {call_id} not found in active calls to finalize.")
            return

        metrics = self.active_calls[call_id]
        update_metrics_from_result(metrics, response, success, error)
        metrics.finalize()

        self.exporter.update_metrics(metrics)
        self.exporter.update_active_calls_gauge(
            metrics.provider, metrics.model, increment=False
        )

        del self.active_calls[call_id]
        log_call_completion(call_id, metrics, success)
