# tests/unit/memory/test_consolidation_worker.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.consolidation_worker import ConsolidationManager


@pytest.mark.asyncio
async def test_should_consolidate_count_threshold():
    """should_consolidate returns True if count >= 20."""
    manager = ConsolidationManager()
    result = await manager.should_consolidate("chat123", 20)
    assert result is True


@pytest.mark.asyncio
async def test_should_consolidate_inactivity_threshold():
    """should_consolidate returns True if elapsed activity > 6 hours."""
    manager = ConsolidationManager()

    # Mock RedisMessageBuffer
    mock_buffer = MagicMock()
    # 21601 seconds ago
    import time

    mock_buffer.get_last_activity = AsyncMock(return_value=time.time() - 21601)

    with patch(
        "src.memory.long_term_memory.long_term_memory.get_buffer",
        AsyncMock(return_value=mock_buffer),
    ):
        result = await manager.should_consolidate("chat123", 5)
        assert result is True


@pytest.mark.asyncio
async def test_consolidate_session_empty_buffer():
    """consolidate_session returns early if buffer is empty."""
    manager = ConsolidationManager()

    mock_buffer = MagicMock()
    mock_buffer.get_messages = AsyncMock(return_value=[])

    with (
        patch(
            "src.memory.long_term_memory.long_term_memory.get_buffer",
            AsyncMock(return_value=mock_buffer),
        ),
        patch(
            "src.memory.long_term_memory.long_term_memory.update_memory", AsyncMock()
        ) as mock_update,
    ):
        await manager.consolidate_session("chat123")
        mock_update.assert_not_called()
