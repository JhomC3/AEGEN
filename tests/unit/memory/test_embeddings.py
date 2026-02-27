from unittest.mock import AsyncMock, patch

import pytest

from src.memory.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_embed_texts():
    with patch("src.memory.embeddings.GoogleGenerativeAIEmbeddings") as MockEmbedder:
        # Configurar mock asíncrono
        mock_instance = MockEmbedder.return_value
        mock_instance.aembed_documents = AsyncMock(
            return_value=[[0.1] * 768, [0.2] * 768]
        )

        # Necesitamos simular la configuración de API Key
        with patch("src.core.config.settings.GOOGLE_API_KEY") as mock_key:
            mock_key.get_secret_value.return_value = "fake_key"

            service = EmbeddingService()
            texts = ["hola", "mundo"]
            embeddings = await service.embed_texts(texts)

            assert len(embeddings) == 2
            assert len(embeddings[0]) == 768
            mock_instance.aembed_documents.assert_called_once()


@pytest.mark.asyncio
async def test_embed_query():
    with patch("src.memory.embeddings.GoogleGenerativeAIEmbeddings") as MockEmbedder:
        mock_instance = MockEmbedder.return_value
        mock_instance.aembed_query = AsyncMock(return_value=[0.3] * 768)

        with patch("src.core.config.settings.GOOGLE_API_KEY") as mock_key:
            mock_key.get_secret_value.return_value = "fake_key"

            service = EmbeddingService()
            embedding = await service.embed_query("buscar algo")

            assert len(embedding) == 768
            assert embedding[0] == 0.3
