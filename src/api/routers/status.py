# src/api/routers/status.py
import logging
import time
from typing import Any, cast

from fastapi import APIRouter, Depends, status

from src.core.config import settings
from src.core.dependencies import get_event_bus, get_sqlite_store
from src.core.interfaces.bus import IEventBus
from src.core.registry import specialist_registry
from src.core.schemas import (
    AppEnvironment,
    HealthCheckResponse,
    HealthStatus,
    ServiceHealth,
    ServiceStatus,
)

router = APIRouter()
logger = logging.getLogger(__name__)

event_bus_dependency = Depends(get_event_bus)


# --- Cache para Salud de Servicios Pesados ---
_llm_health_cache: dict[str, Any] = {"status": None, "timestamp": 0}
LLM_HEALTH_CACHE_TTL = 300  # 5 minutos (300 segundos)


# --- Funciones de Chequeo de Servicios Reales ---
async def check_vector_db() -> ServiceStatus:
    """Verifica la conectividad real de la base de datos de vectores (SQLite)."""
    try:
        store = get_sqlite_store()
        db = await store.get_db()
        # Una consulta simple para verificar la conexión
        async with db.execute("SELECT 1") as cursor:
            await cursor.fetchone()
        return ServiceStatus.OK
    except Exception as e:
        logger.warning(f"Vector DB health check failed: {e}")
        return ServiceStatus.ERROR


async def check_llm_connection() -> ServiceStatus:
    """
    Verifica la conectividad real del LLM con cache de 5 minutos.
    """
    now = time.time()
    if (
        _llm_health_cache["status"] is not None
        and now - _llm_health_cache["timestamp"] < LLM_HEALTH_CACHE_TTL
    ):
        return cast(ServiceStatus, _llm_health_cache["status"])

    try:
        from src.core.engine import check_llm_health

        health_data = await check_llm_health()
        if health_data.get("status") == "healthy":
            result = ServiceStatus.OK
        else:
            result = ServiceStatus.ERROR
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")
        result = ServiceStatus.ERROR

    # Actualizar cache
    _llm_health_cache["status"] = result
    _llm_health_cache["timestamp"] = now
    return result


async def _check_service(name: str, check_fn: Any) -> tuple[ServiceHealth, bool]:
    """Helper para ejecutar un chequeo de servicio y retornar el estado."""
    status = await check_fn()
    is_healthy = status == ServiceStatus.OK
    return ServiceHealth(
        name=name,
        status=status,
        details="Connected" if is_healthy else "Connection failed",
    ), is_healthy


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Status"],
    summary="Verifica la salud de la aplicación.",
    status_code=status.HTTP_200_OK,
)
async def health_check(
    event_bus: IEventBus = event_bus_dependency,
) -> HealthCheckResponse:
    """
    Verifica la salud de la aplicación y sus dependencias críticas.
    """
    logger.info("Health check requested.")

    service_checks: list[ServiceHealth] = []
    overall_healthy: bool = True

    # 1. Vector DB
    sh, ok = await _check_service("vector_db", check_vector_db)
    service_checks.append(sh)
    if not ok:
        overall_healthy = False

    # 2. LLM Connection
    sh, ok = await _check_service("llm_connection", check_llm_connection)
    service_checks.append(sh)
    if not ok:
        overall_healthy = False

    # 3. Event Bus
    eb_status = ServiceStatus.OK if event_bus else ServiceStatus.ERROR
    eb_healthy = eb_status == ServiceStatus.OK
    service_checks.append(
        ServiceHealth(
            name="event_bus",
            status=eb_status,
            details="Initialized" if eb_healthy else "Not available",
        )
    )
    if not eb_healthy:
        overall_healthy = False

    return HealthCheckResponse(
        status=HealthStatus.HEALTHY if overall_healthy else HealthStatus.DEGRADED,
        environment=AppEnvironment(settings.APP_ENV.value),
        services=service_checks,
    )


@router.get(
    "/llm-health",
    tags=["Status"],
    summary="Verifica la salud del proveedor LLM activo",
)
async def llm_health_check() -> dict[str, Any]:
    """
    Verifica la conexión y salud del proveedor LLM configurado.
    """
    from src.core.engine import check_llm_health

    return await check_llm_health()


@router.get(
    "/specialists",
    tags=["Debug"],
    summary="Debug: Lista especialistas registrados",
)
def get_specialists() -> dict[str, Any]:
    """Debug endpoint para verificar especialistas registrados."""
    specialists = specialist_registry.get_all_specialists()
    return {
        "count": len(specialists),
        "specialists": [
            {
                "name": s.name,
                "type": type(s).__name__,
                "capabilities": s.get_capabilities(),
            }
            for s in specialists
        ],
    }
