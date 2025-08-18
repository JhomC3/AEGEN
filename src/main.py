import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from prometheus_fastapi_instrumentator import Instrumentator

# Importar los especialistas para asegurar que se registren al inicio
from src import agents  # noqa: F401
from src.api.routers import analysis, status, webhooks
from src.core.config import settings
from src.core.dependencies import (
    initialize_global_resources,
    prime_dependencies,
    shutdown_global_resources,
)
from src.core.error_handling import register_exception_handlers
from src.core.logging_config import setup_logging
from src.core.middleware import CorrelationIdMiddleware

setup_logging()

logger = logging.getLogger(settings.APP_NAME)


# --- Ciclo de vida de la aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Lifespan: Starting up {settings.APP_NAME} in '{settings.APP_ENV.value}' mode (Version: {settings.APP_VERSION})..."
    )
    logger.info(f"Lifespan: Debug mode is {'ON' if settings.DEBUG_MODE else 'OFF'}.")

    redis_client, event_bus = await initialize_global_resources()

    if redis_client and settings.REDIS_URL:
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

    # "Calienta" las dependencias singleton y suscribe los workers
    prime_dependencies()
    # TODO: Reemplazar la lógica del antiguo WorkflowCoordinator con el nuevo MasterRouter
    # coordinator = get_workflow_coordinator()
    # await event_bus.subscribe("workflow_tasks", coordinator.handle_workflow_event)

    logger.info("Lifespan: Application startup complete.")
    yield
    logger.info(f"Lifespan: Shutting down {settings.APP_NAME}...")
    await shutdown_global_resources()
    logger.info("Lifespan: Application shutdown complete.")


# --- Aplicación FastAPI ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para análisis blockchain multi-agente, impulsada por IA.",
    lifespan=lifespan,
    debug=settings.DEBUG_MODE,
    openapi_tags=[
        {"name": "Status", "description": "Endpoints de estado y monitoreo de la API."},
        {
            "name": "Analysis",
            "description": "Operaciones principales de análisis y ingestión.",
        },
    ],
)

# --- Middleware ---
app.add_middleware(CorrelationIdMiddleware)

if settings.ALLOWED_HOSTS == ["*"]:
    logger.warning(
        "CORS 'allow_origins' está configurado como '*' (permitir todo). Considera restringirlo en producción."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not settings.DEBUG_MODE and settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    logger.info(f"TrustedHostMiddleware enabled for hosts: {settings.ALLOWED_HOSTS}")


# --- Métricas de Prometheus ---
Instrumentator().instrument(app).expose(app)
logger.info("Prometheus Instrumentator configured. Metrics available at /metrics.")


# --- Manejadores de Excepciones ---
register_exception_handlers(app)


# --- Routers ---
app.include_router(status.router, prefix="/system", tags=["System"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

logger.info(f"FastAPI application '{settings.APP_NAME}' configured and ready.")


# --- Punto de entrada para Uvicorn (si se ejecuta directamente) ---
if __name__ == "__main__":
    logger.info(
        f"Running {settings.APP_NAME} directly with Uvicorn. This is for development only."
    )
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
