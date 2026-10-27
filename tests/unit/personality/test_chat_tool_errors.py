"""Regresión: el fallo del LLM no debe convertirse en respuesta exitosa (spec 002)."""

from unittest.mock import AsyncMock

import pytest

from src.personality.skills.chat import tools as chat_tools


@pytest.mark.asyncio
async def test_fallo_del_llm_se_propaga(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        chat_tools.user_profile_manager,
        "load_profile",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        chat_tools.user_profile_manager,
        "get_personality_adaptation",
        lambda _profile: {"history_limit": 10},
    )
    monkeypatch.setattr(
        chat_tools.system_prompt_builder,
        "build",
        AsyncMock(return_value=[("system", "prompt de prueba")]),
    )

    def _get_llm_fallido(_call_name: str) -> None:
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(chat_tools, "get_llm", _get_llm_fallido)

    with pytest.raises(RuntimeError, match="proveedor caído"):
        await chat_tools.conversational_chat_tool.ainvoke({
            "user_message": "hola",
            "chat_id": "123",
            "rag_context": {
                "semantic_fragments": [],
                "evolution_note": "Perfil activo.",
                "structured_facts": [],
            },
        })
