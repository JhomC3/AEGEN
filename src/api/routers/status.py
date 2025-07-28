# src/api/routers/status.py
import logging

from fastapi import (
    APIRouter,
    Depends,
    status,
)

# Importar desde el archivo correcto
# Import dependencies for healthcheck (e.g., Orchestrator Agent)
# Asume que estos existen para el ejemplo de inyección de dependencia
# y que OrchestratorAgent tiene un método get_state() que retorna un Enum o un valor comparable
from src.agents.orchestrator import OrchestratorAgent
from src.core.config import settings

# Import status for HTTP status codes
from src.core.dependencies import (
    get_orchestrator_agent,
)
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


# --- Funciones de Chequeo de Servicios (placeholders) ---
# Estas funciones simulan el chequeo de la salud de servicios externos.
# En una aplicación real, harían llamadas a bases de datos, APIs externas, etc.
async def check_vector_db() -> ServiceStatus:
    """
    Simulates checking vector database connectivity.
    Replace with actual logic (e.g., ping DB, simple query).
    """
    try:
        # Example: Simulating a potential failure
        # if settings.APP_ENV == AppEnvironment.LOCAL and some_condition_for_failure:
        #     raise ConnectionRefusedError("Simulated vector DB connection error")
        return ServiceStatus.OK
    except Exception:
        # Log the actual exception for debugging in a real scenario
        logger.error("Failed to connect to vector database.", exc_info=True)
        return ServiceStatus.ERROR


async def check_llm_connection() -> ServiceStatus:
    """
    Simulates checking LLM connectivity.
    Replace with actual logic (e.g., a simple LLM API call).
    """
    try:
        # Example: Simulating a potential failure
        # if some_other_condition_for_failure:
        #     raise TimeoutError("Simulated LLM connection timeout")
        return ServiceStatus.OK
    except Exception:
        logger.error("Failed to connect to LLM service.", exc_info=True)
        return ServiceStatus.ERROR


# --- Endpoints ---


@router.get("/", response_model=StatusResponse, tags=["Status"])
async def read_root() -> StatusResponse:
    """Simple Root Endpoint"""
    logger.debug("Root endpoint '/' called")
    return StatusResponse(
        status=f"{settings.APP_NAME} API is running!",
        environment=AppEnvironment(
            settings.APP_ENV.value
        ),  # Usamos el valor de la cadena de la enumeración
        version=settings.APP_VERSION,
    )


orchestrator_dependency = Depends(get_orchestrator_agent)


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Status"],
    summary="Verifies the health of the application and its critical dependencies.",
    status_code=status.HTTP_200_OK,  # Default status code is 200 OK
)
async def health_check(
    # Inject necessary dependencies to check services
    # Example with DI:
    orchestrator: OrchestratorAgent = orchestrator_dependency,
) -> HealthCheckResponse:
    """
    Verifies the health of the application and its critical dependencies.
    Returns 200 OK if healthy, or 200 OK with degraded status if some dependencies fail.
    Consider returning a 5xx status code in case of critical, unrecoverable failures.
    """
    logger.info("Health check requested.")

    service_checks: list[ServiceHealth] = []
    overall_healthy: bool = True

    # Check Vector DB
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

    # Check LLM Connection
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

    # Check Orchestrator State (example with DI)
    orchestrator_service_status: ServiceStatus
    orchestrator_details: str
    orchestrator_agent_state = (
        "running"  # Placeholder, debe ser implementado en el agente
    )
    try:
        # Assuming orchestrator.get_state() returns an Enum or a string that can be mapped
        # orchestrator_agent_state = await orchestrator.get_state()
        # Adapt this logic based on actual OrchestratorAgent.get_state() return value
        if orchestrator_agent_state == "running":  # Example: if "running" means OK
            orchestrator_service_status = ServiceStatus.OK
            orchestrator_details = "Agent is running"
        else:
            orchestrator_service_status = (
                ServiceStatus.DEGRADED
            )  # Or ERROR based on state
            orchestrator_details = f"Agent state: {orchestrator_agent_state}"
            overall_healthy = False
    except Exception as e:
        logger.error(f"Orchestrator state check failed: {e}", exc_info=True)
        orchestrator_service_status = ServiceStatus.ERROR
        orchestrator_details = f"Failed to get agent state: {e}"
        overall_healthy = False

    service_checks.append(
        ServiceHealth(
            name="orchestrator_agent",
            status=orchestrator_service_status,
            details=orchestrator_details,
        )
    )

    main_status = HealthStatus.HEALTHY if overall_healthy else HealthStatus.DEGRADED

    # If any service is in ERROR, it might be worth considering a 503 Service Unavailable,
    # but for simple health checks, 200 OK with 'degraded' status is common.
    # For critical unrecoverable failures, you might raise an HTTPException:
    # if main_status == HealthStatus.UNHEALTHY:
    #     raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Application is unhealthy")

    return HealthCheckResponse(
        status=main_status,
        environment=AppEnvironment(
            settings.APP_ENV.value
        ),  # Usamos el valor de la cadena de la enumeración
        services=service_checks,
    )
