# src/api/routers/status.py
import logging

from fastapi import APIRouter, Depends, status

from src.core.config import settings
from src.core.dependencies import get_event_bus
from src.core.engine import MigrationDecisionEngine
from src.core.interfaces.bus import IEventBus
from src.core.schemas import (
    AppEnvironment,
    HealthCheckResponse,
    HealthStatus,
    ServiceHealth,
    ServiceStatus,
    StatusResponse,
    SystemStatus,
)

router = APIRouter()
logger = logging.getLogger(__name__)

event_bus_dependency = Depends(get_event_bus)


# --- Funciones de Chequeo de Servicios (placeholders) ---
async def check_vector_db() -> ServiceStatus:
    """Simula la comprobación de la conectividad de la base de datos de vectores."""
    return ServiceStatus.OK


async def check_llm_connection() -> ServiceStatus:
    """Simula la comprobación de la conectividad del LLM."""
    return ServiceStatus.OK


# --- Endpoints ---


@router.get("/", response_model=StatusResponse, tags=["Status"])
async def read_root() -> StatusResponse:
    """Endpoint raíz simple."""
    logger.debug("Root endpoint '/' called")
    return StatusResponse(
        status=f"{settings.APP_NAME} API is running!",
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
    "/status",
    response_model=SystemStatus,
    tags=["Status"],
    summary="Evalúa el estado del sistema y si debe migrar a una arquitectura distribuida.",
)
def get_system_status() -> SystemStatus:
    """
    Ejecuta el motor de decisión de migración para determinar si los recursos
    del sistema han superado los umbrales predefinidos.
    """
    logger.info("System status check requested.")
    engine = MigrationDecisionEngine()
    status = engine.get_system_status()
    return status
