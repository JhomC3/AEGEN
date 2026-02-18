# src/core/dependencies.py
import logging
from functools import lru_cache

from fastapi import HTTPException, status
from redis import asyncio as aioredis

from src.core.bus.in_memory import InMemoryEventBus
from src.core.bus.redis import RedisEventBus
from src.core.config import settings
from src.core.conversation_memory import ConversationMemory
from src.core.interfaces.bus import IEventBus
from src.core.role_manager import RoleManager
from src.core.security.access_controller import AccessController
from src.core.session_manager import session_manager
from src.core.user_preferences import UserPreferences
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_memory_manager import VectorMemoryManager

logger = logging.getLogger(__name__)

# --- Gestión de Recursos Globales (ej. cliente Redis) ---
redis_connection: aioredis.Redis | None = None
event_bus: IEventBus | None = None
sqlite_store: SQLiteStore | None = None


async def initialize_global_resources() -> tuple[aioredis.Redis | None, IEventBus]:
    """Inicializa recursos globales como Redis y el bus de eventos."""
    global redis_connection, event_bus, sqlite_store

    import os

    from src.memory.backup import CloudBackupManager

    # 1. Recuperación Automática (si la DB no existe y tenemos bucket configurado)
    if not os.path.exists(settings.SQLITE_DB_PATH) and settings.GCS_BACKUP_BUCKET:
        logger.info("Database not found locally. Attempting restore from GCS...")
        backup_mgr = CloudBackupManager()
        await backup_mgr.restore_latest()

    # 2. Inicializar SQLite
    try:
        sqlite_store = SQLiteStore(settings.SQLITE_DB_PATH)
        await sqlite_store.init_db(settings.SQLITE_SCHEMA_PATH)
        logger.info("SQLiteStore initialized and schema applied.")

        from src.memory.migration import apply_migrations

        await apply_migrations(sqlite_store)
        logger.info("Database migrations applied.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLiteStore: {e}")
        # Consideramos SQLite crítico para el nuevo sistema
        raise

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


async def shutdown_global_resources() -> None:
    """Cierra conexiones y recursos globales."""
    if sqlite_store:
        await sqlite_store.disconnect()
        logger.info("SQLite connection closed.")

    if isinstance(event_bus, (RedisEventBus, InMemoryEventBus)):
        await event_bus.shutdown()
        logger.info("Event Bus shut down.")

    if redis_connection:
        await redis_connection.close()
        logger.info("Redis connection closed.")


# --- Inyección de Dependencias ---


def get_event_bus() -> IEventBus:
    """
    Dependencia de FastAPI para obtener la instancia del bus de eventos.
    """
    if event_bus is None:
        # Esto no debería ocurrir si el lifespan se ejecuta correctamente
        raise RuntimeError("Event bus has not been initialized.")
    return event_bus


# Dependencia para obtener la conexión Redis (si algún componente la necesita)
async def get_redis_dependency() -> aioredis.Redis:
    if redis_connection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection not available.",
        )
    return redis_connection


def get_conversation_memory() -> ConversationMemory:
    """FastAPI dependency para ConversationMemory."""
    return ConversationMemory(session_manager=session_manager)


def get_user_preferences() -> UserPreferences:
    """FastAPI dependency para UserPreferences."""
    return UserPreferences(vector_memory_manager=get_vector_memory_manager())


def get_role_manager() -> RoleManager:
    """FastAPI dependency para RoleManager."""
    return RoleManager(vector_memory_manager=get_vector_memory_manager())


@lru_cache
def get_vector_memory_manager() -> VectorMemoryManager:
    """FastAPI dependency para VectorMemoryManager."""
    from src.memory.vector_memory_manager import VectorMemoryManager

    # Inyectar el store global para evitar re-inicialización de sqlite-vec
    store = get_sqlite_store()
    return VectorMemoryManager(store=store)


def get_access_controller() -> AccessController:
    """FastAPI dependency para AccessController."""
    logger.debug("Creating/providing AccessController instance.")
    return AccessController()


def get_sqlite_store() -> SQLiteStore:
    """FastAPI dependency para SQLiteStore."""
    if sqlite_store is None:
        raise RuntimeError("SQLiteStore has not been initialized.")
    return sqlite_store


def prime_dependencies() -> None:
    """
    "Calienta" las dependencias singleton al arranque de la aplicación.
    """
    get_role_manager()
    get_access_controller()
    logger.info("Primed singleton dependencies.")
