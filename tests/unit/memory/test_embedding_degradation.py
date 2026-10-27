"""Regresiones de degradación de memoria cuando embeddings falla (spec 002)."""

import threading
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.memory.embeddings import EmbeddingService
from src.memory.hybrid_search import HybridSearch


@pytest.mark.asyncio
async def test_busqueda_hibrida_cae_a_keyword_si_embeddings_falla() -> None:
    hybrid = HybridSearch(store=MagicMock())
    hybrid.embedding_service.embed_query = AsyncMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("API_KEY_INVALID")
    )
    hybrid.vector_search.search = AsyncMock(  # type: ignore[method-assign]
        return_value=[(9, 0.1)]
    )
    hybrid.keyword_search.search = AsyncMock(  # type: ignore[method-assign]
        return_value=[(1, -1.0)]
    )
    hybrid._hydrate = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {
                "id": 1,
                "content": "recuerdo por palabra clave",
                "memory_type": "fact",
                "metadata": {},
                "score": 0.5,
                "chat_id": "u1",
                "created_at": None,
            }
        ]
    )

    results = await hybrid.search("consulta", limit=5)

    assert [r["id"] for r in results] == [1]
    hybrid.vector_search.search.assert_not_awaited()
    hybrid.keyword_search.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_embedding_se_ejecuta_fuera_del_event_loop() -> None:
    hilos: list[threading.Thread] = []

    def _embed_falso(**_kwargs: Any) -> dict[str, list[list[float]]]:
        hilos.append(threading.current_thread())
        return {"embedding": [[0.1] * 768]}

    service = EmbeddingService.__new__(EmbeddingService)
    service.model_name = "models/gemini-embedding-001"
    service.store = None

    with patch("src.memory.embeddings.genai.embed_content", side_effect=_embed_falso):
        result = await service.embed_texts(["hola"])

    assert len(result) == 1
    assert hilos and hilos[0] is not threading.main_thread()


def test_sin_clave_no_tumba_el_arranque(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(EmbeddingService, "_configured", False)

    service = EmbeddingService()

    assert service is not None
