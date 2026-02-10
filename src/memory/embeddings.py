# src/memory/embeddings.py
"""
Embedding service for generating vector representations of text.

Uses Google GenAI gemini-embedding-001 model with 768 dimensions.
"""

import logging

import google.generativeai as genai

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper para el servicio de embeddings de Google.
    Genera vectores de 768 dimensiones usando gemini-embedding-001.
    """

    _configured: bool = False

    def __init__(self, model_name: str = "models/gemini-embedding-001"):
        """
        Inicializa el cliente de Google GenAI una sola vez (Singleton-like config).
        """
        self.model_name = model_name

        if not EmbeddingService._configured:
            api_key = (
                settings.GOOGLE_API_KEY.get_secret_value()
                if settings.GOOGLE_API_KEY
                else None
            )

            if not api_key:
                logger.error("GOOGLE_API_KEY not found in settings")
                raise ValueError("GOOGLE_API_KEY is required for EmbeddingService")

            genai.configure(api_key=api_key)
            EmbeddingService._configured = True
            logger.info(
                f"EmbeddingService configured for first time with model: {model_name}"
            )
        else:
            logger.debug(
                f"EmbeddingService already configured. Reusing connection for {model_name}"
            )

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """
        Genera embeddings para una lista de textos.

        Args:
            texts: Lista de fragmentos de texto
            task_type: Tipo de tarea para Google (RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY)

        Returns:
            Lista de vectores (listas de floats)
        """
        if not texts:
            return []

        try:
            # Google GenAI SDK (actualmente sincrónico, pero lo envolvemos en async)
            response = genai.embed_content(
                model=self.model_name,
                content=texts,
                task_type=task_type,
                output_dimensionality=768,
            )

            # genai.embed_content devuelve un diccionario con la llave 'embedding'
            # que es una lista de vectores si content es una lista de strings
            embeddings = response.get("embedding", [])
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    async def embed_query(self, query: str) -> list[float]:
        """
        Genera embedding para una búsqueda (query).
        """
        embeddings = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else []
