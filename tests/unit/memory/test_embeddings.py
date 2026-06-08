# tests/unit/memory/test_embeddings.py
from unittest.mock import AsyncMock, patch

import pytest

from src.memory.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_embed_texts():
    with patch("google.generativeai.embed_content") as mock_embed:
        mock_embed.return_value = {"embedding": [[0.1] * 768, [0.2] * 768]}

        with patch("src.core.config.settings.GOOGLE_API_KEY") as mock_key:
            mock_key.get_secret_value.return_value = "fake_key"
            EmbeddingService._configured = False

            service = EmbeddingService()
            with (
                patch.object(service, "_get_cached_embedding", return_value=None),
                patch.object(service, "_save_cached_embedding", new_callable=AsyncMock),
            ):
                texts = ["hola", "mundo"]
                embeddings = await service.embed_texts(texts)

                assert len(embeddings) == 2
                assert len(embeddings[0]) == 768
                mock_embed.assert_called_once()


@pytest.mark.asyncio
async def test_embed_query():
    with patch("google.generativeai.embed_content") as mock_embed:
        mock_embed.return_value = {"embedding": [[0.3] * 768]}

        with patch("src.core.config.settings.GOOGLE_API_KEY") as mock_key:
            mock_key.get_secret_value.return_value = "fake_key"
            EmbeddingService._configured = False

            service = EmbeddingService()
            with (
                patch.object(service, "_get_cached_embedding", return_value=None),
                patch.object(service, "_save_cached_embedding", new_callable=AsyncMock),
            ):
                embedding = await service.embed_query("buscar algo")

                assert len(embedding) == 768
                assert embedding[0] == pytest.approx(0.3)
