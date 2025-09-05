# src/core/observability/prometheus_metrics.py
"""
Configuración de métricas Prometheus para observabilidad LLM.
Responsabilidad única: Definición de métricas Prometheus.
"""

from prometheus_client import Counter, Histogram, Gauge

# === Prometheus Metrics ===

# Counters
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM calls by provider, model, and call type',
    ['provider', 'model', 'call_type', 'success']
)

llm_tokens_total = Counter(
    'llm_tokens_total', 
    'Total tokens consumed by provider, model, and token type',
    ['provider', 'model', 'token_type']
)

# Histograms for latency
llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'LLM call latency in seconds by provider and model',
    ['provider', 'model', 'call_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Gauge for active calls
llm_active_calls = Gauge(
    'llm_active_calls',
    'Number of active LLM calls by provider and model',
    ['provider', 'model']
)

# Cost tracking
llm_cost_total = Counter(
    'llm_cost_total',
    'Estimated total cost in USD by provider and model',
    ['provider', 'model']
)