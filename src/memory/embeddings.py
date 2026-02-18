import logging
from typing import cast

import google.generativeai as genai

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper para el servicio de embeddings de Google.
    """

    _configured: bool = False

    def __init__(self, model_name: str = "models/gemini-embedding-001") -> None:
        """Inicializa el cliente de Google GenAI."""
        self.model_name = model_name

        if not EmbeddingService._configured:
            api_key = (
                settings.GOOGLE_API_KEY.get_secret_value()
                if settings.GOOGLE_API_KEY
                else None
            )

            if not api_key:
                logger.error("GOOGLE_API_KEY not found in settings")
                raise ValueError("GOOGLE_API_KEY is required")

            genai.configure(api_key=api_key)
            EmbeddingService._configured = True
            logger.info("EmbeddingService configured: %s", model_name)
        else:
            logger.debug("Reusing EmbeddingService for %s", model_name)

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Genera embeddings para una lista de textos."""
        if not texts:
            return []

        try:
            # SDK sincrónico envuelto en async implicito por la arquitectura
            response = genai.embed_content(
                model=self.model_name,
                content=texts,
                task_type=task_type,
                output_dimensionality=768,
            )

            embeddings = response.get("embedding", [])
            logger.debug("Generated %d embeddings", len(embeddings))
            return cast(list[list[float]], embeddings)

        except Exception as e:
            logger.error("Error generating embeddings: %s", e)
            raise

    async def embed_query(self, query: str) -> list[float]:
        """Genera embedding para una búsqueda."""
        embeddings = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else []
