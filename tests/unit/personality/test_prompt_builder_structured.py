# tests/unit/personality/test_prompt_builder_structured.py
from unittest.mock import AsyncMock, patch

import pytest

from src.personality.prompt_builder import system_prompt_builder
from src.personality.types import PersonalityBase, SkillOverlay


class TestPromptBuilderStructured:
    """Tests del nuevo build() que retorna lista de mensajes."""

    @pytest.fixture
    def mock_base(self) -> PersonalityBase:
        return PersonalityBase(
            identity={"nombre": "MAGI", "naturaleza": "Tu amigo cercano"},
            soul="# SOUL.md\n## Core Truths\n1. Soy genuinamente útil",
        )

    @pytest.fixture
    def mock_overlay(self) -> SkillOverlay:
        return SkillOverlay(
            name="chat",
            tone_modifiers="- Directo y ultra-eficiente",
            instructions="1. Responde de forma concisa",
            anti_patterns="- Distancia técnica",
            linguistic_rules="- Eco Léxico",
        )

    @pytest.mark.asyncio
    async def test_build_returns_list_of_messages(
        self, mock_base: PersonalityBase, mock_overlay: SkillOverlay
    ) -> None:
        """build() retorna lista de tuplas (role, content) para ChatPromptTemplate."""
        with (
            patch(
                "src.personality.prompt_builder.personality_manager.get_base",
                new_callable=AsyncMock,
            ) as mock_get_base,
            patch(
                "src.personality.prompt_builder.personality_manager.get_skill_overlay",
                new_callable=AsyncMock,
            ) as mock_get_overlay,
        ):
            mock_get_base.return_value = mock_base
            mock_get_overlay.return_value = mock_overlay

            result = await system_prompt_builder.build(
                profile={"identity": {"name": "Test"}, "localization": {}},
                skill_name="chat",
                runtime_context={"history_summary": "Resumen"},
                recent_user_messages=["Hola"],
            )

            # Verificar que retorna lista de mensajes
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(msg, tuple) and len(msg) == 2 for msg in result)
            assert all(msg[0] == "system" for msg in result)

    @pytest.mark.asyncio
    async def test_build_no_manual_escape(
        self, mock_base: PersonalityBase, mock_overlay: SkillOverlay
    ) -> None:
        """build() NO hace .replace('{', '{{') manualmente."""
        with (
            patch(
                "src.personality.prompt_builder.personality_manager.get_base",
                new_callable=AsyncMock,
            ) as mock_get_base,
            patch(
                "src.personality.prompt_builder.personality_manager.get_skill_overlay",
                new_callable=AsyncMock,
            ) as mock_get_overlay,
        ):
            mock_get_base.return_value = mock_base
            mock_get_overlay.return_value = mock_overlay

            result = await system_prompt_builder.build(
                profile={"identity": {"name": "Test"}, "localization": {}},
                skill_name="chat",
                runtime_context={
                    "history_summary": "Resumen con {variable}",
                },
                recent_user_messages=["Hola"],
            )

            # Verificar que el contenido NO tiene {{ escapado manualmente
            full_prompt = "\n".join([msg[1] for msg in result])
            # {variable} debe aparecer como tal, no como {{variable}}
            # (LangChain maneja el escape internamente)
            assert "{{variable}}" not in full_prompt
