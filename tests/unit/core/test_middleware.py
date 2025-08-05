# tests/unit/core/test_middleware.py
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.core.middleware import CorrelationIdMiddleware, correlation_id


@pytest.mark.asyncio
async def test_middleware_uses_existing_correlation_id():
    """
    Verifica que el middleware reutiliza el X-Correlation-ID si ya existe en la petición.
    """
    # Crear un scope de petición falso
    scope = {"type": "http", "headers": [(b"x-correlation-id", b"test-id-123")]}
    request = Request(scope)

    # Mock de la función 'call_next' que será llamada por el middleware
    async def call_next(request: Request) -> Response:
        # Dentro del endpoint, verificar que el ID de contexto es el correcto
        assert correlation_id.get() == "test-id-123"
        return Response("OK", status_code=200)

    middleware = CorrelationIdMiddleware(app=AsyncMock())
    response = await middleware.dispatch(request, call_next)

    # Verificar que la respuesta contiene la misma cabecera
    assert response.headers["X-Correlation-ID"] == "test-id-123"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_middleware_generates_new_correlation_id():
    """
    Verifica que el middleware genera un nuevo ID si no viene en la petición.
    """
    # Petición sin cabecera de correlación
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    generated_id = None

    async def call_next(request: Request) -> Response:
        nonlocal generated_id
        # Capturar el ID generado desde el contexto
        generated_id = correlation_id.get()
        assert generated_id is not None
        assert len(generated_id) == 32  # UUID4 hex es de 32 caracteres
        return Response("OK", status_code=200)

    middleware = CorrelationIdMiddleware(app=AsyncMock())
    response = await middleware.dispatch(request, call_next)

    # Verificar que la cabecera de respuesta coincide con el ID generado
    assert response.headers["X-Correlation-ID"] == generated_id
    assert response.status_code == 200
