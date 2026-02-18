from src.core.observability.metrics import LLMCallMetrics
from src.core.observability.prometheus_metrics import (
    llm_active_calls,
    llm_calls_total,
    llm_cost_total,
    llm_latency_seconds,
    llm_tokens_total,
)


class PrometheusLLMExporter:
    """Exports LLM metrics to Prometheus."""

    def update_metrics(self, metrics: LLMCallMetrics) -> None:
        """Actualiza métricas de Prometheus."""
        success_label = "success" if metrics.success else "failure"

        self._update_call_counter(metrics, success_label)
        self._update_token_counters(metrics)
        self._update_latency_histogram(metrics)
        self._update_cost_counter(metrics)

    def _update_call_counter(self, metrics: LLMCallMetrics, success_label: str) -> None:
        """Actualiza contador de llamadas."""
        llm_calls_total.labels(
            provider=metrics.provider,
            model=metrics.model,
            call_type=metrics.call_type,
            success=success_label,
        ).inc()

    def _update_token_counters(self, metrics: LLMCallMetrics) -> None:
        """Actualiza contadores de tokens."""
        if metrics.input_tokens:
            llm_tokens_total.labels(
                provider=metrics.provider, model=metrics.model, token_type="input"
            ).inc(metrics.input_tokens)  # noqa: S106

        if metrics.output_tokens:
            llm_tokens_total.labels(
                provider=metrics.provider, model=metrics.model, token_type="output"
            ).inc(metrics.output_tokens)  # noqa: S106

    def _update_latency_histogram(self, metrics: LLMCallMetrics) -> None:
        """Actualiza histograma de latencia."""
        if metrics.latency_ms:
            llm_latency_seconds.labels(
                provider=metrics.provider,
                model=metrics.model,
                call_type=metrics.call_type,
            ).observe(metrics.latency_ms / 1000)

    def _update_cost_counter(self, metrics: LLMCallMetrics) -> None:
        """Actualiza contador de costos."""
        if metrics.estimated_cost_usd:
            llm_cost_total.labels(provider=metrics.provider, model=metrics.model).inc(
                metrics.estimated_cost_usd
            )

    def update_active_calls_gauge(
        self, provider: str, model: str, increment: bool
    ) -> None:
        """Actualiza gauge de llamadas activas."""
        gauge = llm_active_calls.labels(provider=provider, model=model)
        if increment:
            gauge.inc()
        else:
            gauge.dec()
