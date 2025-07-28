# src/core/dependencies.py
import logging
from functools import lru_cache

from fastapi import HTTPException, status
from redis import asyncio as aioredis

# Importar clases de Agentes (¡Asegúrate de que los archivos existan!)
from src.agents.orchestrator import WorkflowCoordinator
from src.core.bus.in_memory import InMemoryEventBus
from src.core.config import settings
from src.core.interfaces.bus import IEventBus

# from .planner import PlannerAgent
# from .analyst import AnalystAgent
# ... etc ...

logger = logging.getLogger(__name__)

# --- Gestión de Recursos Globales (ej. cliente Redis) ---
redis_connection = None
event_bus: IEventBus | None = None


async def initialize_global_resources():
    """Inicializa recursos globales como Redis y el bus de eventos."""
    global redis_connection, event_bus
    try:
        redis_connection = aioredis.from_url(
            settings.REDIS_URL, encoding="utf8", decode_responses=True
        )
        await redis_connection.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_connection = None  # Marcar como no disponible

    # Inicializar el bus de eventos
    # En Fase 1, es siempre en memoria. En Fase 2, esto podría leer config.
    event_bus = InMemoryEventBus()
    logger.info("Event Bus initialized (InMemoryEventBus).")

    return redis_connection, event_bus


async def shutdown_global_resources():
    """Cierra conexiones y recursos globales."""
    if redis_connection:
        await redis_connection.close()
        logger.info("Redis connection closed.")

    if isinstance(event_bus, InMemoryEventBus):
        await event_bus.shutdown()
        logger.info("Event Bus shut down.")


# --- Inyección de Dependencias ---


@lru_cache
def get_workflow_coordinator() -> WorkflowCoordinator:
    """
    Proporciona una instancia singleton del coordinador de workflows.
    Este coordinador es el principal consumidor de eventos del bus.
    """
    logger.debug("Creating/providing WorkflowCoordinator instance.")
    return WorkflowCoordinator()


def get_event_bus() -> IEventBus:
    """
    Dependencia de FastAPI para obtener la instancia del bus de eventos.
    """
    if event_bus is None:
        # Esto no debería ocurrir si el lifespan se ejecuta correctamente
        raise RuntimeError("Event bus has not been initialized.")
    return event_bus


# Dependencia para obtener la conexión Redis (si algún componente la necesita)
async def get_redis_dependency():
    if redis_connection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection not available.",
        )
    return redis_connection


def prime_dependencies():
    """
    "Calienta" las dependencias singleton al arranque de la aplicación.
    """
    get_workflow_coordinator()
    logger.info("Primed singleton dependencies.")
