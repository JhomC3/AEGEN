# tests/unit/memory/test_ephemeral_guard.py
from unittest.mock import AsyncMock, patch

import pytest

from src.memory.long_term_memory import LongTermMemoryManager


@pytest.mark.asyncio
async def test_store_raw_message_skips_in_ephemeral_mode():
    """When ephemeral_mode=True, store_raw_message must not persist anything."""
    manager = LongTermMemoryManager()

    mock_profile = {
        "memory_settings": {"ephemeral_mode": True, "consent_given": True},
        "metadata": {"version": "1.2.0"},
    }

    with patch("src.core.profile_manager.user_profile_manager") as mock_pm:
        mock_pm.load_profile = AsyncMock(return_value=mock_profile)

        mock_buffer = AsyncMock()
        with patch.object(manager, "get_buffer", AsyncMock(return_value=mock_buffer)):
            await manager.store_raw_message("chat123", "user", "Hello world")

            # Buffer should NOT be called
            mock_buffer.push_message.assert_not_called()


@pytest.mark.asyncio
async def test_store_raw_message_persists_when_ephemeral_false():
    """When ephemeral_mode=False, store_raw_message must persist normally."""
    manager = LongTermMemoryManager()

    mock_profile = {
        "memory_settings": {"ephemeral_mode": False, "consent_given": True},
        "metadata": {"version": "1.2.0"},
    }

    with patch("src.core.profile_manager.user_profile_manager") as mock_pm:
        mock_pm.load_profile = AsyncMock(return_value=mock_profile)

        mock_buffer = AsyncMock()
        mock_buffer.push_message = AsyncMock()
        mock_buffer.get_message_count = AsyncMock(return_value=1)

        with patch.object(manager, "get_buffer", AsyncMock(return_value=mock_buffer)):
            with patch(
                "src.memory.consolidation_worker.consolidation_manager"
            ) as mock_cm:
                mock_cm.should_consolidate = AsyncMock(return_value=False)

                await manager.store_raw_message("chat123", "user", "Hello world")

                # Buffer SHOULD be called
                mock_buffer.push_message.assert_called_once_with(
                    "chat123", "user", "Hello world"
                )
