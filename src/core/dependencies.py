# src/core/dependencies.py
import logging
from functools import lru_cache

from fastapi import HTTPException, status
from redis import asyncio as aioredis

# Importar clases de Agentes (¡Asegúrate de que los archivos existan!)
from src.agents.orchestrator import OrchestratorAgent
from src.core.config import settings

# from .planner import PlannerAgent
# from .analyst import AnalystAgent
# ... etc ...

logger = logging.getLogger(__name__)

# --- Gestión de Recursos Globales (ej. cliente Redis) ---
redis_connection = None


async def initialize_global_resources():
    global redis_connection
    try:
        redis_connection = aioredis.from_url(
            settings.REDIS_URL, encoding="utf8", decode_responses=True
        )
        await redis_connection.ping()
        logger.info("Successfully connected to Redis.")
        return redis_connection
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_connection = None  # Marcar como no disponible
        return None


async def shutdown_global_resources():
    if redis_connection:
        await redis_connection.close()
        logger.info("Redis connection closed.")


# --- Inyección de Dependencias (Factorías para Agentes) ---


# Usar lru_cache para crear singletons de agentes si es apropiado
# (Cuidado si los agentes tienen estado mutable por request)
@lru_cache
def get_orchestrator_agent() -> OrchestratorAgent:
    logger.debug("Creating/providing OrchestratorAgent instance.")
    # Aquí podrías inyectar otras dependencias si Orchestrator las necesita
    # por ejemplo, planner=get_planner_agent()
    return OrchestratorAgent()  # Asume inicialización simple o interna


# Ejemplo para otro agente que necesite config o recursos
# @lru_cache()
# def get_planner_agent() -> PlannerAgent:
#    logger.debug("Creating/providing PlannerAgent instance.")
#    return PlannerAgent(llm_model=settings.DEFAULT_LLM_MODEL)


# Dependencia para obtener la conexión Redis (si algún agente la necesita directamente)
async def get_redis_dependency():
    if redis_connection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection not available.",
        )
    return redis_connection


# Inicializa todos los agentes necesarios al arrancar si usan @lru_cache
# Opcional: Podría hacerse en lifespan para asegurar creación temprana
def prime_agent_dependencies():
    get_orchestrator_agent()
    # get_planner_agent()
    logger.info("Primed singleton agent dependencies.")
