# ruff: noqa: UP043
import os
import threading
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


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Force-exit if idle executor threads would block process shutdown.

    aiofiles uses loop.run_in_executor() which spawns non-daemon
    ThreadPoolExecutor workers (e.g. 'asyncio_0'). These threads have
    a ~60s idle timeout and prevent the process from exiting after tests
    complete. By the time this hook fires (trylast=True), all test results
    and coverage data have already been collected and written.
    """
    non_daemon = [
        t
        for t in threading.enumerate()
        if not t.daemon and t.name != "MainThread" and t.is_alive()
    ]
    if non_daemon:
        os._exit(exitstatus)  # noqa: SIM112
