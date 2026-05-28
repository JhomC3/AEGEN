# tests/unit/memory/test_reranker.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.reranker import SemanticReranker


@pytest.mark.asyncio
async def test_reranker_sorting_logic():
    # Creamos un mock completo de la cadena de langchain
    mock_chain = AsyncMock()

    # Simular respuesta JSON de relevancia de Gemini
    # Le da máxima prioridad al déficit calórico (index 0) para una consulta sobre fitness
    mock_json_response = '[{"index": 0, "relevance": 0.95}, {"index": 1, "relevance": 0.1}, {"index": 2, "relevance": 0.3}]'

    mock_response = MagicMock()
    mock_response.content = mock_json_response
    mock_chain.ainvoke.return_value = mock_response

    # Parcheamos la construcción de la cadena prompt | llm en rerank
    with patch(
        "langchain_core.prompts.ChatPromptTemplate.__or__", return_value=mock_chain
    ):
        reranker = SemanticReranker()

        candidates = [
            {
                "id": 1,
                "content": "El déficit calórico sostenido es clave para quemar grasa.",
            },
            {
                "id": 2,
                "content": "La Terapia Cognitiva Conductual ayuda a reestructurar pensamientos.",
            },
            {"id": 3, "content": "El gasto impulsivo puede denotar ansiedad."},
        ]

        results = await reranker.rerank(
            query="¿Cómo bajar de peso de forma saludable?",
            candidates=candidates,
            top_k=2,
        )

        assert mock_chain.ainvoke.call_count == 1
        assert len(results) == 2
        # El primero debe ser el index 0 (ID 1)
        assert results[0]["id"] == 1
        assert results[0]["score"] == 0.95

        # El segundo debe ser el index 2 (ID 3) con score 0.3 (mayor que index 1 con 0.1)
        assert results[1]["id"] == 3
        assert results[1]["score"] == 0.3
