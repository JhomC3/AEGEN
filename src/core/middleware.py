from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_CTX_KEY: Final[str] = "correlation_id"
correlation_id: ContextVar[str | None] = ContextVar(
    CORRELATION_ID_CTX_KEY, default=None
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add a correlation ID to every request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Dispatches the request, adding a correlation ID.

        Args:
            request: The incoming request.
            call_next: The next function to call in the middleware chain.

        Returns:
            The response from the next middleware.
        """
        # Intenta obtener el ID de correlación de la cabecera de la solicitud.
        # Si no está presente, genera un nuevo UUID.
        correlation_id_value = request.headers.get("X-Correlation-ID")
        if not correlation_id_value:
            correlation_id_value = uuid.uuid4().hex

        # Establece el ID de correlación en la ContextVar.
        correlation_id.set(correlation_id_value)

        # Procesa la solicitud y obtén la respuesta.
        response = await call_next(request)

        # Añade el ID de correlación a las cabeceras de la respuesta.
        response.headers["X-Correlation-ID"] = correlation_id_value

        return response
