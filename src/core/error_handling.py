import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import AppBaseError  # Importar tu excepción base

logger = logging.getLogger(__name__)


async def app_base_exception_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, AppBaseError):
        return await generic_exception_handler(request, exc)
    logger.error(
        f"AppBaseException caught: {exc.message} (Status: {exc.status_code}) "
        f"for URL {request.url.path}",
        exc_info=(exc.status_code >= 500),  # Loguea traceback para errores 5xx
        extra={"status_code": exc.status_code, "detail": exc.detail},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):
        return await generic_exception_handler(request, exc)
    logger.warning(
        f"HTTPException caught: {exc.status_code} - {exc.detail} "
        f"for URL {request.url.path}",
        extra={"status_code": exc.status_code, "detail": exc.detail},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Este es el último recurso para excepciones no manejadas.
    logger.critical(
        f"Unhandled critical exception: {exc.__class__.__name__} - {str(exc)} "
        f"for URL {request.url.path}",
        exc_info=True,  # Siempre loguea traceback para excepciones inesperadas
        extra={"exception_type": exc.__class__.__name__},
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "An unexpected internal server error occurred. Please contact support."
            )
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppBaseError, app_base_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    # El manejador genérico debe ser el último en ser añadido
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Custom application exception handlers registered.")
