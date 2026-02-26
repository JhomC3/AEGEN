import asyncio
import logging
from typing import cast

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper para el servicio de embeddings de Google con Rate Limiting y Batching.
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
        """Genera embeddings procesando en lotes pequeños para evitar 429 Rate Limits."""
        if not texts:
            return []

        all_embeddings = []
        batch_size = (
            100  # Límite seguro por debajo del límite de cuota (3000 rpm / 100 rp-req)
        )

        # Procesar en lotes
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            logger.info(
                f"Procesando lote de embeddings: {i} a {i + len(batch_texts)} de {len(texts)}"
            )

            # Sistema de reintentos exponencial interno para cada lote
            max_retries = 3
            base_delay = 10

            for attempt in range(max_retries):
                try:
                    # SDK sincrónico envuelto en async implicito por la arquitectura
                    response = genai.embed_content(
                        model=self.model_name,
                        content=batch_texts,
                        task_type=task_type,
                        output_dimensionality=768,
                    )

                    batch_embeddings = response.get("embedding", [])
                    all_embeddings.extend(batch_embeddings)
                    break  # Éxito, salir del bucle de reintentos

                except google_exceptions.ResourceExhausted:
                    if attempt == max_retries - 1:
                        logger.error(
                            "Agotados los reintentos para el lote. Rate Limit superado."
                        )
                        raise
                    delay = base_delay * (2**attempt)  # 10s, 20s, 40s
                    logger.warning(
                        f"Rate Limit 429. Esperando {delay}s antes de reintentar (intento {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"Error fatal generando embeddings en lote: {e}")
                    raise

            # Breve pausa entre lotes exitosos para no saturar la cuota por minuto de Google
            if i + batch_size < len(texts):
                await asyncio.sleep(2)

        logger.debug("Generated %d embeddings successfully", len(all_embeddings))
        return cast(list[list[float]], all_embeddings)

    async def embed_query(self, query: str) -> list[float]:
        """Genera embedding para una búsqueda."""
        embeddings = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else []
