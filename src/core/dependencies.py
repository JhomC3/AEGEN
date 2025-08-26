# src/core/dependencies.py
import logging
from functools import lru_cache

import chromadb
from chromadb.utils import embedding_functions
from fastapi import HTTPException, status
from redis import asyncio as aioredis

# Importar clases de Agentes (¡Asegúrate de que los archivos existan!)
# from src.agents.orchestrator import WorkflowCoordinator
from src.core.bus.in_memory import InMemoryEventBus
from src.core.bus.redis import RedisEventBus
from src.core.config import settings
from src.core.interfaces.bus import IEventBus
from src.vector_db.chroma_manager import ChromaManager
from src.core.vector_memory_manager import VectorMemoryManager
from src.core.conversation_memory import ConversationMemory
from src.core.user_preferences import UserPreferences
from src.core.role_manager import RoleManager
from src.core.secure_chroma_manager import SecureChromaManager
from src.core.session_manager import session_manager

# from .planner import PlannerAgent
# from .analyst import AnalystAgent
# ... etc ...

logger = logging.getLogger(__name__)

# --- Gestión de Recursos Globales (ej. cliente Redis) ---
redis_connection: aioredis.Redis | None = None
event_bus: IEventBus | None = None


async def initialize_global_resources() -> tuple[aioredis.Redis | None, IEventBus]:
    """Inicializa recursos globales como Redis y el bus de eventos."""
    global redis_connection, event_bus
    try:
        # Usamos decode_responses=False porque nuestro RedisEventBus maneja la (de)serialización
        redis_connection = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
        await redis_connection.ping()
        logger.info("Successfully connected to Redis.")
        # Si Redis está disponible, usamos RedisEventBus
        event_bus = RedisEventBus(redis_connection)
        logger.info("Event Bus initialized (RedisEventBus).")
    except Exception as e:
        logger.error(
            f"Failed to connect to Redis: {e}. Falling back to InMemoryEventBus."
        )
        redis_connection = None  # Marcar como no disponible
        event_bus = InMemoryEventBus()
        logger.info("Event Bus initialized (InMemoryEventBus).")

    return redis_connection, event_bus


async def shutdown_global_resources():
    """Cierra conexiones y recursos globales."""
    if isinstance(event_bus, RedisEventBus) or isinstance(event_bus, InMemoryEventBus):
        await event_bus.shutdown()
        logger.info("Event Bus shut down.")

    if redis_connection:
        await redis_connection.close()
        logger.info("Redis connection closed.")


# --- Inyección de Dependencias ---


# @lru_cache
# def get_workflow_coordinator() -> WorkflowCoordinator:
#     """
#     Proporciona una instancia singleton del coordinador de workflows.
#     Este coordinador es el principal consumidor de eventos del bus.
#     """
#     logger.debug("Creating/providing WorkflowCoordinator instance.")
#     return WorkflowCoordinator()


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


# --- ChromaDB Dependencies ---


@lru_cache()
def get_chroma_client() -> chromadb.HttpClient:
    """
    Provides ChromaDB HttpClient instance with async support.
    Uses configuration from settings for different environments.
    """
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST, 
            port=settings.CHROMA_PORT
        )
        logger.info(f"ChromaDB HttpClient initialized: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        raise


@lru_cache()
def get_embedding_function():
    """Provides consistent embedding function for all ChromaDB collections."""
    return embedding_functions.DefaultEmbeddingFunction()


def get_chroma_manager(
    client: chromadb.HttpClient = None,
    embedding_function = None
) -> ChromaManager:
    """
    FastAPI dependency to provide ChromaManager with injected dependencies.
    
    Args:
        client: ChromaDB HttpClient (will be injected by FastAPI)
        embedding_function: Embedding function (will be injected by FastAPI)
    """
    if client is None:
        client = get_chroma_client()
    if embedding_function is None:
        embedding_function = get_embedding_function()
        
    return ChromaManager(client=client, embedding_function=embedding_function)


def get_vector_memory_manager(
    chroma_manager: ChromaManager = None
) -> VectorMemoryManager:
    """FastAPI dependency para VectorMemoryManager."""
    if chroma_manager is None:
        chroma_manager = get_chroma_manager()
        
    return VectorMemoryManager(
        chroma_manager=chroma_manager,
        session_manager=session_manager
    )


def get_conversation_memory(
    vector_memory_manager: VectorMemoryManager = None
) -> ConversationMemory:
    """FastAPI dependency para ConversationMemory."""
    if vector_memory_manager is None:
        vector_memory_manager = get_vector_memory_manager()
        
    return ConversationMemory(vector_memory_manager)


def get_user_preferences(
    vector_memory_manager: VectorMemoryManager = None
) -> UserPreferences:
    """FastAPI dependency para UserPreferences."""
    if vector_memory_manager is None:
        vector_memory_manager = get_vector_memory_manager()
        
    return UserPreferences(vector_memory_manager)


def get_role_manager(
    vector_memory_manager: VectorMemoryManager = None
) -> RoleManager:
    """FastAPI dependency para RoleManager."""
    if vector_memory_manager is None:
        vector_memory_manager = get_vector_memory_manager()
        
    return RoleManager(vector_memory_manager)


def get_secure_chroma_manager(
    chroma_manager: ChromaManager = None,
    role_manager: RoleManager = None
) -> SecureChromaManager:
    """FastAPI dependency para SecureChromaManager."""
    if chroma_manager is None:
        chroma_manager = get_chroma_manager()
    if role_manager is None:
        role_manager = get_role_manager()
        
    return SecureChromaManager(chroma_manager, role_manager)


@lru_cache
def get_file_handler_agent() -> "FileHandlerAgent":
    """FastAPI dependency para FileHandlerAgent."""
    from src.agents.file_handler_agent import FileHandlerAgent
    logger.debug("Creating/providing FileHandlerAgent instance.")
    return FileHandlerAgent()


def prime_dependencies():
    """
    "Calienta" las dependencias singleton al arranque de la aplicación.
    """
    # get_workflow_coordinator()
    get_chroma_client()
    get_embedding_function()
    get_vector_memory_manager()
    get_role_manager()
    get_file_handler_agent()
    logger.info("Primed singleton dependencies including VectorMemoryManager, RoleManager, and FileHandlerAgent.")
