# tests/unit/core/test_profile_manager_style.py
from unittest.mock import AsyncMock, patch

import pytest

from src.core.profile_manager import user_profile_manager
from src.personality.types import StyleSignals


class TestProfileManagerStyle:
    """Tests de persistencia de StyleSignals en profiles."""

    @pytest.mark.asyncio
    async def test_update_style_signals_adds_field(self) -> None:
        """update_style_signals agrega style_signals al perfil."""
        test_profile = {
            "identity": {"name": "Test", "chat_id": "test_chat"},
            "metadata": {"last_updated": "2024-01-01"},
        }

        with patch.object(
            user_profile_manager, "load_profile", new_callable=AsyncMock
        ) as mock_load, patch.object(
            user_profile_manager, "save_profile", new_callable=AsyncMock
        ) as mock_save:
            # load_profile retorna test_profile, luego save_profile guarda
            mock_load.return_value = test_profile

            signals = StyleSignals(
                detected_language="es",
                formality_indicator="casual",
                brevity="conciso",
                uses_emoji=True,
            )
            await user_profile_manager.update_style_signals("test_chat", signals)

            # Verificar que save_profile fue llamado con el perfil modificado
            mock_save.assert_called_once()
            saved_profile = mock_save.call_args[0][1]
            assert saved_profile["style_signals"]["detected_language"] == "es"
            assert saved_profile["style_signals"]["formality_indicator"] == "casual"
            assert saved_profile["style_signals"]["uses_emoji"] is True
            # Verificar que campos originales se preservan
            assert saved_profile["identity"]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_update_style_signals_overwrites_previous(self) -> None:
        """update_style_signals sobrescribe señales previas."""
        test_profile = {
            "identity": {"name": "Test", "chat_id": "test_chat"},
            "metadata": {"last_updated": "2024-01-01"},
            "style_signals": {
                "detected_language": "pt",
                "formality_indicator": "casual",
                "brevity": "conciso",
                "uses_emoji": False,
            },
        }

        with patch.object(
            user_profile_manager, "load_profile", new_callable=AsyncMock
        ) as mock_load, patch.object(
            user_profile_manager, "save_profile", new_callable=AsyncMock
        ) as mock_save:
            mock_load.return_value = test_profile

            signals = StyleSignals(
                detected_language="en",
                formality_indicator="formal",
                brevity="verboso",
                uses_emoji=False,
            )
            await user_profile_manager.update_style_signals("test_chat", signals)

            mock_save.assert_called_once()
            saved_profile = mock_save.call_args[0][1]
            # Debe tener el nuevo idioma
            assert saved_profile["style_signals"]["detected_language"] == "en"
            assert saved_profile["style_signals"]["formality_indicator"] == "formal"
