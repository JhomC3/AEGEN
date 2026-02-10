# src/api/routers/status.py
import logging
import time
from typing import Any

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
    StatusResponse,
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
    Verifica la conectividad real del LLM con cache de 5 minutos
    para evitar rate limiting y reducir latencia en el healthcheck.
    """
    now = time.time()
    if (
        _llm_health_cache["status"] is not None
        and now - _llm_health_cache["timestamp"] < LLM_HEALTH_CACHE_TTL
    ):
        return _llm_health_cache["status"]

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


# --- Endpoints ---


@router.get("/", response_model=StatusResponse, tags=["Status"])
async def read_root() -> StatusResponse:
    """Endpoint raíz simple."""
    logger.debug("Root endpoint '/' called")
    return StatusResponse(
        status="MAGI API is running!",
        environment=AppEnvironment(settings.APP_ENV.value),
        version=settings.APP_VERSION,
    )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Status"],
    summary="Verifica la salud de la aplicación y sus dependencias críticas.",
    status_code=status.HTTP_200_OK,
)
async def health_check(
    event_bus: IEventBus = event_bus_dependency,
) -> HealthCheckResponse:
    """
    Verifica la salud de la aplicación y sus dependencias críticas.
    Devuelve 200 OK si está saludable, o con estado degradado si algunas dependencias fallan.
    """
    logger.info("Health check requested.")

    service_checks: list[ServiceHealth] = []
    overall_healthy: bool = True

    # Comprobar Vector DB
    vector_db_status = await check_vector_db()
    service_checks.append(
        ServiceHealth(
            name="vector_db",
            status=vector_db_status,
            details=(
                "Connected"
                if vector_db_status == ServiceStatus.OK
                else "Connection failed"
            ),
        )
    )
    if vector_db_status != ServiceStatus.OK:
        overall_healthy = False

    # Comprobar Conexión LLM
    llm_connection_status = await check_llm_connection()
    service_checks.append(
        ServiceHealth(
            name="llm_connection",
            status=llm_connection_status,
            details=(
                "Connected"
                if llm_connection_status == ServiceStatus.OK
                else "Connection failed"
            ),
        )
    )
    if llm_connection_status != ServiceStatus.OK:
        overall_healthy = False

    # Comprobar Event Bus
    event_bus_status = ServiceStatus.OK
    event_bus_details = "Event Bus is initialized."
    if not event_bus:
        event_bus_status = ServiceStatus.ERROR
        event_bus_details = "Event Bus is not available."
        overall_healthy = False

    service_checks.append(
        ServiceHealth(
            name="event_bus", status=event_bus_status, details=event_bus_details
        )
    )

    main_status = HealthStatus.HEALTHY if overall_healthy else HealthStatus.DEGRADED

    return HealthCheckResponse(
        status=main_status,
        environment=AppEnvironment(settings.APP_ENV.value),
        services=service_checks,
    )


@router.get(
    "/llm-health",
    tags=["Status"],
    summary="Verifica la salud del proveedor LLM activo",
)
async def llm_health_check():
    """
    Verifica la conexión y salud del proveedor LLM configurado.
    """
    from src.core.engine import check_llm_health

    health_data = await check_llm_health()
    return health_data


@router.get(
    "/specialists",
    tags=["Debug"],
    summary="Debug: Lista especialistas registrados",
)
def get_specialists():
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
