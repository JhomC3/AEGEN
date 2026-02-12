# tests/unit/memory/test_incremental_extractor.py
from unittest.mock import AsyncMock, patch

import pytest

from src.memory.services.incremental_extractor import (
    _background_semaphore,
    incremental_fact_extraction,
)


class TestIncrementalExtractorThrottle:
    """Verifica que la extracción incremental tiene límite de concurrencia."""

    def test_semaphore_exists(self):
        """Debe existir un semáforo global para limitar concurrencia."""
        assert _background_semaphore is not None
        # Máximo 1 extracción simultánea
        assert _background_semaphore._value == 1

    @pytest.mark.asyncio
    async def test_skips_when_semaphore_busy(self):
        """Si ya hay una extracción en curso, la nueva se descarta."""
        # Adquirir el semáforo para simular tarea en curso
        await _background_semaphore.acquire()
        try:
            buffer = AsyncMock()
            buffer.get_messages.return_value = [{"role": "user", "content": "test"}]
            # Esta llamada debe ser descartada (no-op)
            with patch(
                "src.memory.services.incremental_extractor.fact_extractor"
            ) as mock_fe:
                await incremental_fact_extraction("test_chat", buffer)
                mock_fe.extract_facts.assert_not_called()
        finally:
            _background_semaphore.release()
