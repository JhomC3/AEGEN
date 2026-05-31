"""Tests de busqueda en historial de conversaciones."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_search_conversation_history_returns_results() -> None:
    """La busqueda debe retornar fragmentos de conversacion relevantes."""
    from src.tools.session_search import search_conversation_history

    mock_results = [
        {
            "content": "Hablamos sobre deficit calorico",
            "created_at": "2026-05-20T10:00:00",
        },
    ]

    with patch(
        "src.tools.session_search._keyword_search_conversations",
        new_callable=AsyncMock,
        return_value=mock_results,
    ):
        result = await search_conversation_history.ainvoke({
            "query": "dieta",
            "chat_id": "123",
            "days_back": 30,
        })

    assert "deficit calorico" in result


@pytest.mark.asyncio
async def test_search_conversation_history_empty_returns_message() -> None:
    """Si no hay resultados, retornar mensaje informativo."""
    from src.tools.session_search import search_conversation_history

    with patch(
        "src.tools.session_search._keyword_search_conversations",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await search_conversation_history.ainvoke({
            "query": "inexistente",
            "chat_id": "123",
            "days_back": 30,
        })

    assert isinstance(result, str)
    assert len(result) > 0
