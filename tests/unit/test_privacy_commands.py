# tests/unit/test_privacy_commands.py
from unittest.mock import AsyncMock, patch

import pytest

from src.api.routers.privacy import handle_privacy_command


@pytest.mark.asyncio
async def test_privacidad_returns_stats():
    """The /privacidad command must return memory statistics."""
    mock_store = AsyncMock()
    mock_store.get_memory_stats.return_value = {
        "total": 42,
        "by_type": {"fact": 20, "conversation": 22},
        "by_sensitivity": {"low": 30, "medium": 10, "high": 2},
    }

    with patch("src.api.routers.privacy.get_sqlite_store", return_value=mock_store):
        response = await handle_privacy_command("/privacidad", "chat123")

    assert response is not None
    assert "42" in response
    assert "Hecho" in response or "fact" in response.lower()


@pytest.mark.asyncio
async def test_olvidar_deletes_matching_memories():
    """/olvidar should soft-delete memories matching the topic."""
    mock_vmm = AsyncMock()
    mock_vmm.delete_memories_by_query.return_value = 3

    with patch(
        "src.api.routers.privacy.get_vector_memory_manager", return_value=mock_vmm
    ):
        response = await handle_privacy_command("/olvidar trabajo", "chat123")

    assert response is not None
    assert "3" in response
    mock_vmm.delete_memories_by_query.assert_called_once_with(
        user_id="chat123",
        query="trabajo",
    )


@pytest.mark.asyncio
async def test_olvidar_without_topic_returns_help():
    response = await handle_privacy_command("/olvidar", "chat123")
    assert response is not None
    assert "tema" in response.lower() or "uso" in response.lower()


@pytest.mark.asyncio
async def test_efimero_toggles_mode():
    """/efimero toggles ephemeral mode in the profile."""
    mock_profile_mgr = AsyncMock()
    mock_profile_mgr.load_profile.return_value = {
        "memory_settings": {
            "ephemeral_mode": False,
            "consent_given": True,
            "sensitivity_threshold": "medium",
        },
        "metadata": {"version": "1.2.0", "last_updated": "2026-01-01"},
    }

    with patch("src.api.routers.privacy.user_profile_manager", mock_profile_mgr):
        response = await handle_privacy_command("/efimero", "chat123")

    assert response is not None
    # Should mention that ephemeral mode is now ON
    assert "activado" in response.lower() or "efímero" in response.lower()
    mock_profile_mgr.save_profile.assert_called_once()


@pytest.mark.asyncio
async def test_unknown_command_returns_none():
    """Non-privacy commands must return None (pass through to orchestrator)."""
    response = await handle_privacy_command("/start", "chat123")
    assert response is None
