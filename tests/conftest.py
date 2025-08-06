# tests/conftest.py
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.dependencies import get_event_bus
from src.core.interfaces.bus import IEventBus
from src.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None, None]:
    """Async test client para la app FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_event_bus() -> Generator[AsyncMock, None, None]:
    """Mock del IEventBus para tests de integración."""
    mock = AsyncMock(spec=IEventBus)
    app.dependency_overrides[get_event_bus] = lambda: mock
    yield mock
    app.dependency_overrides.clear()  # Limpiar después del test
