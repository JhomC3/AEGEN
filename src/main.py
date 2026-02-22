import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from src.core.logging_config import setup_logging

# --- Inicialización de Logs ---
setup_logging()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi_cache import FastAPICache  # noqa: E402
from fastapi_cache.backends.redis import RedisBackend  # noqa: E402
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.error_handling import register_exception_handlers  # noqa: E402
from src.core.middleware import CorrelationIdMiddleware  # noqa: E402

logger = logging.getLogger(settings.APP_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Ciclo de vida asíncrono."""
    logger.info(">>> Arrancando lifespan...")

    from src.core.dependencies import (
        initialize_global_resources,
        prime_dependencies,
        shutdown_global_resources,
    )

    try:
        res = await initialize_global_resources()
        redis_client, _ = res

        if redis_client and settings.REDIS_URL:
            FastAPICache.init(RedisBackend(redis_client), prefix="magi-cache")

        prime_dependencies()

        # Registro diferido de especialistas para romper la cadena de imports eager
        from src.agents.specialists import register_all_specialists

        register_all_specialists()

        from src.memory.global_knowledge_loader import global_knowledge_loader

        asyncio.create_task(global_knowledge_loader.check_and_bootstrap())

        from src.core.messaging.life_reviewer_worker import life_reviewer_worker
        from src.core.messaging.proactive_worker import proactive_worker
        from src.memory.knowledge_watcher import KnowledgeWatcher

        watcher = KnowledgeWatcher(global_knowledge_loader)
        await watcher.start()

        await proactive_worker.start()
        await life_reviewer_worker.start()

        logger.info("Arranque completado.")
        yield

        await life_reviewer_worker.stop()
        await proactive_worker.stop()
        await watcher.stop()
        await shutdown_global_resources()

    except Exception as e:
        logger.critical("Fallo en arranque: %s", e, exc_info=True)
        yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AEGEN Platform.",
    lifespan=lifespan,
    debug=settings.DEBUG_MODE,
)

app.add_middleware(CorrelationIdMiddleware)


@app.middleware("http")
async def log_all_requests(
    request: Request, call_next: Callable[[Request], Any]
) -> Any:
    """Interceptor logs."""
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
Instrumentator().instrument(app).expose(app)

# --- Routers ---
from src.api.routers import (  # noqa: E402
    analysis,
    diagnostics,
    llm_metrics,
    status,
    webhooks,
)

app.include_router(status.router, prefix="/system", tags=["Status"])
app.include_router(llm_metrics.router, prefix="/system/llm")
app.include_router(diagnostics.router, prefix="/system/diagnostics")
app.include_router(analysis.router, prefix="/api/v1/analysis")
app.include_router(webhooks.router, prefix="/api/v1/webhooks")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000)
