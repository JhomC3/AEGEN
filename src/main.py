import asyncio
import logging
from contextlib import asynccontextmanager

from src.core.logging_config import setup_logging

# --- Inicialización de Logs (Debe ser lo primero) ---
setup_logging()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402
from fastapi_cache import FastAPICache  # noqa: E402
from fastapi_cache.backends.redis import RedisBackend  # noqa: E402
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

# Importar los especialistas para asegurar que se registren al inicio
from src import agents  # noqa: F401, E402
from src.api.routers import (  # noqa: E402
    analysis,
    diagnostics,
    llm_metrics,
    status,
    webhooks,
)
from src.core.config import settings  # noqa: E402
from src.core.dependencies import (  # noqa: E402
    initialize_global_resources,
    prime_dependencies,
    shutdown_global_resources,
)
from src.core.error_handling import register_exception_handlers  # noqa: E402
from src.core.middleware import CorrelationIdMiddleware  # noqa: E402

logger = logging.getLogger(settings.APP_NAME)


# --- Ciclo de vida de la aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Ciclo de vida: Arrancando {settings.APP_NAME} en modo '{settings.APP_ENV.value}' (Versión: {settings.APP_VERSION})..."
    )
    logger.info(
        f"Ciclo de vida: Modo depuración (Debug) está {'ENCENDIDO' if settings.DEBUG_MODE else 'APAGADO'}."
    )

    redis_client, event_bus = await initialize_global_resources()

    if redis_client and settings.REDIS_URL:
        try:
            FastAPICache.init(RedisBackend(redis_client), prefix="magi-cache")
            logger.info(
                f"Ciclo de vida: FastAPI Cache inicializado con Redis (URL: {settings.REDIS_URL})."
            )
        except Exception as e:
            logger.error(
                f"Ciclo de vida: Falló la inicialización de FastAPI Cache con Redis: {e}"
            )
    else:
        logger.warning(
            "Ciclo de vida: Cliente Redis no disponible. FastAPI Cache NO inicializado."
        )

    # "Calienta" las dependencias singleton
    prime_dependencies()

    # Validar prompts críticos
    from src.core.prompts.loader import validate_required_prompts

    validate_required_prompts([
        "cbt_therapeutic_response.txt",
    ])

    # --- NUEVO: Arquitectura de Memoria Unificada ---
    # 1. Bootstrap de conocimiento global (En segundo plano para no bloquear el puerto 8000)
    from src.memory.global_knowledge_loader import global_knowledge_loader

    asyncio.create_task(global_knowledge_loader.check_and_bootstrap())

    # 2. Iniciar vigilante de conocimiento (Auto-Sync)
    from src.memory.knowledge_watcher import KnowledgeWatcher

    watcher = KnowledgeWatcher(global_knowledge_loader)
    await watcher.start()

    logger.info("Ciclo de vida: Arquitectura de Memoria Unificada Activa.")
    logger.info("Ciclo de vida: Arranque de la aplicación completado.")
    yield
    logger.info(f"Ciclo de vida: Apagando {settings.APP_NAME}...")

    await watcher.stop()
    await shutdown_global_resources()
    logger.info("Ciclo de vida: Apagado de la aplicación completado.")


# --- Aplicación FastAPI ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma de Agentes Evolutivos AEGEN. MAGI: Asistente Conversacional Inteligente con Especialistas.",
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
# --- Middleware ---
app.add_middleware(CorrelationIdMiddleware)


@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    """Middleware para ver TODAS las peticiones que llegan al servidor (excepto Health Check)."""
    # Silenciar logs de health check para reducir ruido
    is_health_check = request.url.path == "/system/health"

    if not is_health_check:
        logger.info(f">>> PETICIÓN ENTRANTE: {request.method} {request.url.path}")

    response = await call_next(request)

    if not is_health_check:
        logger.info(
            f"<<< RESPUESTA SALIENTE: {request.method} {request.url.path} - Estado: {response.status_code}"
        )
    return response


if ["*"] == settings.ALLOWED_HOSTS:
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

if not settings.DEBUG_MODE and ["*"] != settings.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    logger.info(f"TrustedHostMiddleware enabled for hosts: {settings.ALLOWED_HOSTS}")


# --- Métricas de Prometheus ---
Instrumentator().instrument(app).expose(app)
logger.info("Prometheus Instrumentator configured. Metrics available at /metrics.")


# --- Manejadores de Excepciones ---
register_exception_handlers(app)


# --- Routers ---
app.include_router(status.router, prefix="/system", tags=["System"])
app.include_router(llm_metrics.router, prefix="/system/llm", tags=["LLM Metrics"])
app.include_router(
    diagnostics.router, prefix="/system/diagnostics", tags=["Diagnostics"]
)
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
