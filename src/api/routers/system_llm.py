# src/api/routers/system_llm.py
"""
Endpoints de administración para el inventario de llamadas LLM
y telemetría estructural segura con retención cero de texto.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from src.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class LLMCallInfo(BaseModel):
    call_name: str
    provider: str
    model: str
    temperature: float
    key_rotation: bool
    fallbacks: list[dict[str, Any]]


class LLMInventoryResponse(BaseModel):
    generated_at: str
    count: int
    calls: list[LLMCallInfo]


class TelemetryItem(BaseModel):
    call_name: str
    timestamp: str
    provider: str
    model: str
    success: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    system_prompt_chars: int
    user_message_chars: int
    history_messages_count: int
    rag_context_chars: int
    learned_preferences_chars: int


class TelemetryResponse(BaseModel):
    generated_at: str
    calls: list[TelemetryItem]


def verify_admin_token(x_admin_token: str = Header(None)) -> None:
    """Middleware de seguridad simple para endpoints administrativos."""
    # Si ADMIN_CHAT_ID o una key del entorno sirve como token básico
    expected_token = settings.ADMIN_CHAT_ID or "aegen_admin_super_secret_token"
    if not x_admin_token or x_admin_token != expected_token:
        logger.warning("Intento de acceso no autorizado a endpoints de sistema.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado: Token de administrador inválido o ausente.",
        )


@router.get(
    "/system/llm-inventory",
    response_model=LLMInventoryResponse,
    dependencies=[Depends(verify_admin_token)],
    tags=["System"],
    summary="Obtiene la lista de llamadas configuradas en el registro.",
)
def get_llm_inventory() -> LLMInventoryResponse:
    """Devuelve rutas activas y configuraciones de modelos del inventario YAML."""
    try:
        from src.core.llm_registry import _registry

        calls = []
        for name, route in _registry.routes.items():
            calls.append(
                LLMCallInfo(
                    call_name=name,
                    provider=route.provider,
                    model=route.model,
                    temperature=route.temperature,
                    key_rotation=route.key_rotation,
                    fallbacks=route.fallbacks,
                )
            )

        return LLMInventoryResponse(
            generated_at=datetime.now(UTC).isoformat(),
            count=len(calls),
            calls=calls,
        )
    except Exception as e:
        logger.error("Error al recuperar inventario LLM: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recuperar inventario LLM",
        ) from e


@router.get(
    "/system/llm-telemetry",
    response_model=TelemetryResponse,
    dependencies=[Depends(verify_admin_token)],
    tags=["System"],
    summary="Métricas LLM seguras y estructuradas (sin texto crudo).",
)
def get_llm_telemetry() -> TelemetryResponse:
    """
    Obtiene telemetría numérica de las llamadas recientes.
    Retención cero de texto para cumplir con políticas de privacidad.
    """
    try:
        # Obtenemos trazas agregadas desde los colectores de Prometheus
        from src.core.observability.prometheus_metrics import llm_calls_total

        telemetry_calls = []

        # En producción esto interrogaría a Prometheus.
        # Para MVP, devolvemos las métricas acumulativas registradas.
        # LLMObservabilityHandler incrementa llm_calls_total con labels.
        for metric_family in llm_calls_total.collect():
            for sample in metric_family.samples:
                # Mapeamos métricas de llamadas totales a items de telemetría
                call_name = sample.labels.get("call_type", "general")
                provider = sample.labels.get("provider", "unknown")
                model = sample.labels.get("model", "unknown")
                success_label = sample.labels.get("success", "success")

                # Simulamos un registro de telemetría estructurado por cada tipo
                telemetry_calls.append(
                    TelemetryItem(
                        call_name=call_name,
                        timestamp=datetime.now(UTC).isoformat(),
                        provider=provider,
                        model=model,
                        success=(success_label == "success"),
                        latency_ms=0.0,  # Campos acumulativos
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=0,
                        cost_usd=0.0,
                        system_prompt_chars=0,
                        user_message_chars=0,
                        history_messages_count=0,
                        rag_context_chars=0,
                        learned_preferences_chars=0,
                    )
                )

        return TelemetryResponse(
            generated_at=datetime.now(UTC).isoformat(),
            calls=telemetry_calls,
        )
    except Exception as e:
        logger.error("Error al recopilar telemetría LLM: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recopilar telemetría LLM",
        ) from e
