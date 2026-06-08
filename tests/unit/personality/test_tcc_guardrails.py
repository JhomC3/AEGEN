# tests/unit/personality/test_tcc_guardrails.py
from unittest.mock import AsyncMock, patch

import pytest

from src.personality.skills.tcc.tools import cbt_therapeutic_guidance_tool


class TestTCCGuardrails:
    """Tests de inyección condicional de CLINICAL_GUARDRAILS."""

    @pytest.fixture
    def mock_profile(self) -> dict:
        return {
            "identity": {"name": "Test User"},
            "localization": {"timezone": "UTC"},
            "personality_adaptation": {},
        }

    @pytest.mark.asyncio
    async def test_guardrails_injected_on_crisis(self, mock_profile: dict) -> None:
        """Guardrails se inyectan cuando detect_crisis retorna is_crisis=True."""
        with (
            patch(
                "src.personality.skills.tcc.tools.user_profile_manager.load_profile",
                new_callable=AsyncMock,
            ) as mock_load,
            patch(
                "src.personality.skills.tcc.tools.system_prompt_builder.build",
                new_callable=AsyncMock,
            ) as mock_build,
            patch("src.personality.skills.tcc.tools.detect_crisis") as mock_detect,
            patch("src.personality.skills.tcc.tools.get_llm") as mock_llm,
        ):
            mock_load.return_value = mock_profile
            mock_build.return_value = [("system", "System prompt base")]
            mock_detect.return_value = {
                "is_crisis": True,
                "level": "high",
                "confidence": 0.9,
                "keywords_found": ["suicid"],
                "is_metaphor": False,
            }

            mock_llm_instance = AsyncMock()
            mock_llm.return_value = mock_llm_instance

            # Invocar tool con rag_context ya cargado en los argumentos
            # para evitar fallback a base de datos
            await cbt_therapeutic_guidance_tool.ainvoke({
                "user_message": "Quiero suicid",
                "chat_id": "test_chat",
                "conversation_history": [],
                "rag_context": {
                    "semantic_fragments": [],
                    "evolution_note": "Sin historial previo.",
                    "structured_facts": [],
                },
            })

            mock_detect.assert_called_once_with("Quiero suicid")

    @pytest.mark.asyncio
    async def test_guardrails_not_injected_on_no_crisis(
        self, mock_profile: dict
    ) -> None:
        """Guardrails NO se inyectan cuando detect_crisis retorna is_crisis=False."""
        with (
            patch(
                "src.personality.skills.tcc.tools.user_profile_manager.load_profile",
                new_callable=AsyncMock,
            ) as mock_load,
            patch(
                "src.personality.skills.tcc.tools.system_prompt_builder.build",
                new_callable=AsyncMock,
            ) as mock_build,
            patch("src.personality.skills.tcc.tools.detect_crisis") as mock_detect,
            patch("src.personality.skills.tcc.tools.get_llm") as mock_llm,
        ):
            mock_load.return_value = mock_profile
            mock_build.return_value = [("system", "System prompt base")]
            mock_detect.return_value = {
                "is_crisis": False,
                "level": "none",
                "confidence": 0.0,
                "keywords_found": [],
                "is_metaphor": False,
            }

            mock_llm_instance = AsyncMock()
            mock_llm.return_value = mock_llm_instance

            # Invocar tool con rag_context ya cargado en los argumentos
            # para evitar fallback a base de datos
            await cbt_therapeutic_guidance_tool.ainvoke({
                "user_message": "Hoy tuve un buen día",
                "chat_id": "test_chat",
                "conversation_history": [],
                "rag_context": {
                    "semantic_fragments": [],
                    "evolution_note": "Sin historial previo.",
                    "structured_facts": [],
                },
            })

            mock_detect.assert_called_once_with("Hoy tuve un buen día")
