import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from src.api.routers import analysis as analysis_router
from src.api.routers import status as status_router
from src.core.config import settings
from src.core.dependencies import (
    initialize_global_resources,
    prime_agent_dependencies,
    shutdown_global_resources,
)
from src.core.error_handling import register_exception_handlers

# Configurar logging ANTES de importar cualquier otro módulo de la app que pueda usar logging
from src.core.logging_config import setup_logging

setup_logging()  # ¡Llamar aquí, muy al principio!

logger = logging.getLogger(settings.APP_NAME)  # Obtener logger principal de la app


# --- Ciclo de vida de la aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Lifespan: Starting up {settings.APP_NAME} in '{settings.APP_ENV.value}' mode (Version: {settings.APP_VERSION})..."
    )
    logger.info(f"Lifespan: Debug mode is {'ON' if settings.DEBUG_MODE else 'OFF'}.")

    redis_client = (
        await initialize_global_resources()
    )  # Inicializa Redis, LLM clients, etc.
    if (
        redis_client and settings.REDIS_URL
    ):  # Solo inicializa caché si Redis está disponible
        try:
            FastAPICache.init(RedisBackend(redis_client), prefix="aegen-cache")
            logger.info(
                f"Lifespan: FastAPI Cache initialized with Redis backend (URL: {settings.REDIS_URL})."
            )
        except Exception as e:
            logger.error(
                f"Lifespan: Failed to initialize FastAPI Cache with Redis: {e}"
            )
    else:
        logger.warning(
            "Lifespan: Redis client not available. FastAPI Cache NOT initialized."
        )

    prime_agent_dependencies()  # "Calienta" los singletons de agentes

    logger.info("Lifespan: Application startup complete.")
    yield
    logger.info(f"Lifespan: Shutting down {settings.APP_NAME}...")
    await shutdown_global_resources()  # Limpia Redis, LLM clients, etc.
    logger.info("Lifespan: Application shutdown complete.")


# --- Aplicación FastAPI ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para análisis blockchain multi-agente, impulsada por IA.",
    lifespan=lifespan,
    debug=settings.DEBUG_MODE,  # Controla el modo debug de FastAPI
    # openapi_url="/api/v1/openapi.json", # Si quieres cambiar la URL de OpenAPI
    # docs_url="/api/docs", # Si quieres cambiar la URL de Swagger
    # redoc_url="/api/redoc", # Si quieres cambiar la URL de ReDoc
    openapi_tags=[  # Define tags para agrupar endpoints en Swagger
        {"name": "Status", "description": "Endpoints de estado y monitoreo de la API."},
        {
            "name": "Analysis",
            "description": "Operaciones principales de análisis blockchain.",
        },
        # Puedes añadir más tags para otros grupos de endpoints
    ],
)

# --- Middleware ---
# CORS (Configuración flexible)
if settings.ALLOWED_HOSTS == ["*"]:
    logger.warning(
        "CORS 'allow_origins' está configurado como '*' (permitir todo). Considera restringirlo en producción."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,  # Usa la config de Pydantic
    allow_credentials=True,
    allow_methods=["*"],  # O especifica: ["GET", "POST"]
    allow_headers=["*"],  # O especifica: ["Content-Type", "Authorization"]
)

# Trusted Host (Solo si no es debug y hay hosts definidos)
if not settings.DEBUG_MODE and settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    logger.info(f"TrustedHostMiddleware enabled for hosts: {settings.ALLOWED_HOSTS}")


# --- Manejadores de Excepciones ---
register_exception_handlers(app)


# --- Routers ---
app.include_router(status_router.router)  # Incluye el router de status
app.include_router(
    analysis_router.router, prefix="/api/v1"
)  # Incluye el router de análisis con prefijo

logger.info(f"FastAPI application '{settings.APP_NAME}' configured and ready.")
