"""Tests de activacion data-driven del Graph-RAG."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_graph_rag_activates_when_edges_exist() -> None:
    """Cuando memory_edges tiene aristas para los seed_ids, expand_with_edges debe llamarse."""
    from src.agents.orchestrator.context_retriever import context_retriever_node
    from src.core.schemas.graph import GraphStateV2

    mock_manager = MagicMock()
    mock_manager.retrieve_context = AsyncMock(
        return_value=[
            {"id": 1, "content": "Deficit calórico 400kcal", "score": 0.9},
            {"id": 2, "content": "Irritabilidad los lunes", "score": 0.85},
        ]
    )
    mock_manager.store = MagicMock()

    with (
        patch(
            "src.agents.orchestrator.context_retriever.get_vector_memory_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.agents.orchestrator.context_retriever._check_edges_exist",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check,
        patch(
            "src.memory.graph_search.expand_with_edges",
            new_callable=AsyncMock,
            return_value=[{"id": 3, "content": "Gasto impulsivo"}],
        ) as mock_expand,
        patch(
            "src.agents.orchestrator.context_retriever._load_evolution_note",
            new_callable=AsyncMock,
            return_value=("nota", True),
        ),
        patch(
            "src.memory.reranker.SemanticReranker.rerank",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "content": "Deficit calórico"}],
        ),
    ):
        state = GraphStateV2(
            event=MagicMock(
                chat_id="123", content="¿como afecta mi entrenamiento a mi humor?"
            ),
            payload={"routing_metadata": {"intent": "information_request"}},
            error_message="",
            session_id="",
            conversation_history=[],
            rag_context=None,
        )
        result = await context_retriever_node(state)

    mock_check.assert_awaited_once()
    mock_expand.assert_awaited_once()
    rag_ctx = result.get("rag_context")
    assert rag_ctx is not None
    assert rag_ctx["graph_fragments"] == [{"id": 3, "content": "Gasto impulsivo"}]


@pytest.mark.asyncio
async def test_graph_rag_skips_when_no_edges() -> None:
    """Cuando no hay aristas en memory_edges, expand_with_edges no debe llamarse."""
    from src.agents.orchestrator.context_retriever import context_retriever_node
    from src.core.schemas.graph import GraphStateV2

    mock_manager = MagicMock()
    mock_manager.retrieve_context = AsyncMock(
        return_value=[
            {"id": 1, "content": "Texto sin aristas", "score": 0.8},
        ]
    )
    mock_manager.store = MagicMock()

    with (
        patch(
            "src.agents.orchestrator.context_retriever.get_vector_memory_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.agents.orchestrator.context_retriever._check_edges_exist",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_check,
        patch(
            "src.memory.graph_search.expand_with_edges", new_callable=AsyncMock
        ) as mock_expand,
        patch(
            "src.agents.orchestrator.context_retriever._load_evolution_note",
            new_callable=AsyncMock,
            return_value=("nota", True),
        ),
        patch(
            "src.memory.reranker.SemanticReranker.rerank",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "content": "Texto"}],
        ),
    ):
        state = GraphStateV2(
            event=MagicMock(chat_id="123", content="¿que tal el dia?"),
            payload={"routing_metadata": {"intent": "chat"}},
            error_message="",
            session_id="",
            conversation_history=[],
            rag_context=None,
        )
        result = await context_retriever_node(state)

    mock_check.assert_awaited_once()
    mock_expand.assert_not_awaited()
    rag_ctx = result.get("rag_context")
    assert rag_ctx is not None
