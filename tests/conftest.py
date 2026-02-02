# ruff: noqa: UP043
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:  # noqa: UP043
    """Async test client para la app FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
