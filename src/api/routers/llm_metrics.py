# src/api/routers/llm_metrics.py
"""
Endpoints para métricas LLM y observabilidad.
Responsabilidad única: API endpoints para métricas de observabilidad.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.observability.correlation import get_correlation_id
from src.core.observability.prometheus_metrics import (
    llm_active_calls,
    llm_calls_total,
    llm_cost_total,
    llm_tokens_total,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class LLMStatus(BaseModel):
    """Estado actual del sistema LLM."""

    correlation_id: str
    active_calls: dict[str, float]
    total_calls_today: int
    average_latency_ms: float
    total_cost_today: float
    status: str


class LLMMetricsSummary(BaseModel):
    """Resumen de métricas LLM."""

    total_calls: int
    total_tokens: int
    average_latency_seconds: float
    total_cost_usd: float
    active_calls_count: int


@router.get("/status", response_model=LLMStatus)
async def get_llm_status() -> LLMStatus:
    """
    Obtiene el estado actual del sistema LLM.

    Returns:
        LLMStatus: Estado actual con métricas básicas
    """
    try:
        correlation_id = get_correlation_id()

        # Obtener métricas básicas de Prometheus
        # Nota: En production usaríamos prometheus_client para queries reales
        active_calls_dict = {}
        for metric_family in llm_active_calls.collect():
            for sample in metric_family.samples:
                provider = sample.labels.get('provider', 'unknown')
                model = sample.labels.get('model', 'unknown')
                key = f"{provider}:{model}"
                active_calls_dict[key] = sample.value

        return LLMStatus(
            correlation_id=correlation_id,
            active_calls=active_calls_dict,
            total_calls_today=0,  # TODO: Implementar agregación diaria
            average_latency_ms=0.0,  # TODO: Calcular from histogram
            total_cost_today=0.0,  # TODO: Implementar agregación diaria
            status="operational"
        )

    except Exception as e:
        logger.error(f"Error getting LLM status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving LLM status") from e


@router.get("/metrics/summary", response_model=LLMMetricsSummary)
async def get_llm_metrics_summary() -> LLMMetricsSummary:
    """
    Obtiene resumen de métricas LLM.

    Returns:
        LLMMetricsSummary: Resumen de todas las métricas
    """
    try:
        # Nota: En production esto sería una query a Prometheus
        # Por ahora, obtenemos métricas básicas de los collectors

        total_calls = 0
        total_tokens = 0
        total_cost = 0.0
        active_calls = 0

        # Recopilar métricas de Prometheus collectors
        for metric_family in llm_calls_total.collect():
            for sample in metric_family.samples:
                total_calls += int(sample.value)

        for metric_family in llm_tokens_total.collect():
            for sample in metric_family.samples:
                total_tokens += int(sample.value)

        for metric_family in llm_cost_total.collect():
            for sample in metric_family.samples:
                total_cost += float(sample.value)

        for metric_family in llm_active_calls.collect():
            for sample in metric_family.samples:
                active_calls += int(sample.value)

        return LLMMetricsSummary(
            total_calls=total_calls,
            total_tokens=total_tokens,
            average_latency_seconds=0.0,  # TODO: Calcular from histogram
            total_cost_usd=total_cost,
            active_calls_count=active_calls
        )

    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving metrics summary") from e


@router.get("/health")
async def llm_health_check() -> dict[str, Any]:
    """
    Health check específico para sistema LLM.

    Returns:
        Dict: Estado de salud del sistema LLM
    """
    try:
        correlation_id = get_correlation_id()

        # Verificar que las métricas estén funcionando
        metrics_working = True
        try:
            list(llm_calls_total.collect())
        except Exception:
            metrics_working = False

        return {
            "correlation_id": correlation_id,
            "status": "healthy" if metrics_working else "degraded",
            "metrics_collector": "operational" if metrics_working else "failed",
            "timestamp": "2025-09-04T12:00:00Z"  # TODO: Usar timestamp real
        }

    except Exception as e:
        logger.error(f"LLM health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-09-04T12:00:00Z"
        }
