"""Regresión: la salud LLM no debe declararse sin evidencia (spec 002)."""

from unittest.mock import AsyncMock

import pytest

from src.api.routers import status as status_module
from src.core.schemas import ServiceStatus


@pytest.fixture(autouse=True)
def _cache_limpio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        status_module, "_llm_health_cache", {"status": None, "timestamp": 0}
    )


@pytest.mark.asyncio
async def test_sin_evidencia_reporta_pending() -> None:
    assert await status_module.check_llm_connection() == ServiceStatus.PENDING


@pytest.mark.asyncio
async def test_llm_health_sano_actualiza_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.core.engine.check_llm_health",
        AsyncMock(return_value={"status": "healthy", "latency_ms": 1.0}),
    )

    result = await status_module.llm_health_check()

    assert result["status"] == "healthy"
    assert status_module._llm_health_cache["status"] == ServiceStatus.OK
    assert status_module._llm_health_cache["timestamp"] > 0
    assert await status_module.check_llm_connection() == ServiceStatus.OK


@pytest.mark.asyncio
async def test_llm_health_caido_actualiza_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.core.engine.check_llm_health",
        AsyncMock(return_value={"status": "unhealthy", "error": "sin clave"}),
    )

    await status_module.llm_health_check()

    assert status_module._llm_health_cache["status"] == ServiceStatus.ERROR
    assert await status_module.check_llm_connection() == ServiceStatus.ERROR
