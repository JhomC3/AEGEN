from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.profile_manager import UserProfileManager
from src.memory.consolidation_worker import ConsolidationManager


@pytest.mark.asyncio
async def test_seed_identity_from_platform():
    manager = UserProfileManager()
    manager.load_profile = AsyncMock(return_value={"identity": {"name": "Usuario"}})
    manager.save_profile = AsyncMock()

    # Case 1: Name is "Usuario", should update
    await manager.seed_identity_from_platform("123", "Jhonn")
    manager.save_profile.assert_awaited_once()
    saved_profile = manager.save_profile.call_args[0][1]
    assert saved_profile["identity"]["name"] == "Jhonn"

    # Case 2: Name is already set, should NOT update
    manager.load_profile = AsyncMock(
        return_value={"identity": {"name": "ExistingName"}}
    )
    manager.save_profile = AsyncMock()
    await manager.seed_identity_from_platform("123", "Jhonn")
    manager.save_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_user_name_to_profile():
    # Mock global user_profile_manager
    mock_profile_manager = MagicMock()
    mock_profile_manager.load_profile = AsyncMock(
        return_value={"identity": {"name": "OldName"}}
    )
    mock_profile_manager.save_profile = AsyncMock()

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "src.memory.consolidation_worker.user_profile_manager", mock_profile_manager
        )

        manager = ConsolidationManager()

        # Case 1: New name detected, different from old
        knowledge = {"user_name": "NewName"}
        await manager._sync_user_name_to_profile("123", knowledge)
        mock_profile_manager.save_profile.assert_awaited_once()
        saved_profile = mock_profile_manager.save_profile.call_args[0][1]
        assert saved_profile["identity"]["name"] == "NewName"

        # Case 2: No name detected
        mock_profile_manager.save_profile.reset_mock()
        knowledge = {}
        await manager._sync_user_name_to_profile("123", knowledge)
        mock_profile_manager.save_profile.assert_not_awaited()
