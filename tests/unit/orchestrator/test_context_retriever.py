# tests/unit/orchestrator/test_context_retriever.py
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator.context_retriever import context_retriever_node
from src.core.schemas.graph import CanonicalEventV1, GraphStateV2


@pytest.mark.asyncio
async def test_context_retriever_casual_greeting():
    event = CanonicalEventV1(
        event_type="text", source="telegram", chat_id="123456", content="Hola"
    )

    state: GraphStateV2 = {
        "event": event,
        "payload": {"routing_metadata": {"intent": "casual_greeting"}},
        "error_message": None,
        "session_id": "session_abc",
        "conversation_history": [],
        "rag_context": None,
    }

    # Mock Redis evolution note load
    with patch(
        "src.agents.orchestrator.context_retriever._load_evolution_note",
        return_value=("Hello Jhonn", True),
    ):
        result = await context_retriever_node(state)

        rag = result["rag_context"]
        assert rag is not None
        assert rag["evolution_note"] == "Hello Jhonn"
        assert rag["semantic_fragments"] == []
        assert rag["structured_facts"] == []
        assert rag["cache_hit"] is True


@pytest.mark.asyncio
async def test_context_retriever_analytical_intent():
    event = CanonicalEventV1(
        event_type="text",
        source="telegram",
        chat_id="123456",
        content="Quiero analizar mi déficit calórico e irritabilidad.",
    )

    state: GraphStateV2 = {
        "event": event,
        "payload": {"routing_metadata": {"intent": "life_review"}},
        "error_message": None,
        "session_id": "session_abc",
        "conversation_history": [],
        "rag_context": None,
    }

    # Mock dependencies
    mock_manager = AsyncMock()
    mock_manager.retrieve_context = AsyncMock(
        side_effect=lambda user_id, query, limit, namespace, context_type: [
            {"id": 1, "content": "Fragmento global"}
        ]
        if user_id == "system"
        else [{"id": 2, "content": "Fragmento usuario"}]
    )

    mock_facts = {
        "preferences": [
            {"key": "calorias_meta", "value": "2000", "confidence": 0.95, "evidence": "Definido por nutricionista"}
        ],
        "entities": [],
        "medical": [],
        "relationships": [],
        "milestones": [],
        "user_name": "Jhonn",
    }

    # Mock SemanticReranker to avoid actual API calls and return the candidates directly
    with (
        patch(
            "src.agents.orchestrator.context_retriever._load_evolution_note",
            return_value=(None, False),
        ),
        patch(
            "src.agents.orchestrator.context_retriever.get_vector_memory_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.memory.knowledge_base.knowledge_base_manager.load_knowledge",
            return_value=mock_facts,
        ),
        patch(
            "src.memory.graph_search.expand_with_edges",
            return_value=[{"id": 2, "content": "Fragmento irritabilidad matutina"}],
        ),
        patch(
            "src.memory.reranker.SemanticReranker.rerank",
            side_effect=lambda q, c, top_k: c,
        ),
    ):
        result = await context_retriever_node(state)

        rag = result["rag_context"]
        assert rag is not None
        assert len(rag["semantic_fragments"]) == 2
        assert len(rag["graph_fragments"]) == 1
        assert len(rag["structured_facts"]) == 2
        assert rag["structured_facts"][0]["key"] == "calorias_meta"
        assert rag["structured_facts"][0]["value"] == "2000"
