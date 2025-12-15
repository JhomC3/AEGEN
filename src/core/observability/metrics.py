# src/core/observability/metrics.py
"""
Modelos de datos para métricas LLM.
Responsabilidad única: Definición de estructuras de métricas.
"""

import time
from typing import Any

from pydantic import BaseModel, Field


class LLMCallMetrics(BaseModel):
    """Métricas de una llamada LLM individual."""

    correlation_id: str = Field(..., description="ID de correlación del request")
    provider: str = Field(default="google", description="Proveedor LLM")
    model: str = Field(..., description="Modelo LLM utilizado")
    call_type: str = Field(default="general", description="Tipo de llamada")

    # Timing
    start_time: float = Field(..., description="Timestamp inicio")
    end_time: float | None = Field(None, description="Timestamp fin")
    latency_ms: float | None = Field(None, description="Latencia en ms")

    # Tokens
    input_tokens: int | None = Field(None, description="Tokens entrada")
    output_tokens: int | None = Field(None, description="Tokens salida")
    total_tokens: int | None = Field(None, description="Total tokens")

    # Result
    success: bool = Field(True, description="Llamada exitosa")
    error_message: str | None = Field(None, description="Mensaje error")

    # Cost
    estimated_cost_usd: float | None = Field(None, description="Costo estimado USD")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")

    def finalize(self, end_time: float | None = None) -> None:
        """Finaliza la métrica calculando latencia y tokens totales."""
        self._set_end_time(end_time)
        self._calculate_latency()
        self._calculate_total_tokens()
        self._estimate_cost()

    def _set_end_time(self, end_time: float | None) -> None:
        """Establece el timestamp de fin."""
        self.end_time = end_time or time.time()

    def _calculate_latency(self) -> None:
        """Calcula la latencia en milisegundos."""
        if self.end_time:
            self.latency_ms = (self.end_time - self.start_time) * 1000

    def _calculate_total_tokens(self) -> None:
        """Calcula el total de tokens."""
        if self.input_tokens and self.output_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens

    def _estimate_cost(self) -> None:
        """Estima el costo básico para Gemini."""
        if self.provider == "google" and self.total_tokens:
            # Gemini pricing: ~$0.001 per 1K tokens (estimación aproximada)
            self.estimated_cost_usd = (self.total_tokens / 1000) * 0.001
