import asyncio
import logging
from typing import cast

from google.api_core import exceptions as google_exceptions
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper para el servicio de embeddings usando LangChain nativo.
    Soporta modelos modernos (text-embedding-004) y maneja Rate Limiting/Batching.
    """

    def __init__(self, model_name: str = "models/text-embedding-004") -> None:
        """Inicializa el cliente de Google Embeddings vía LangChain."""
        self.model_name = model_name

        api_key = (
            settings.GOOGLE_API_KEY.get_secret_value()
            if settings.GOOGLE_API_KEY
            else None
        )

        if not api_key:
            logger.error("GOOGLE_API_KEY not found in settings")
            raise ValueError("GOOGLE_API_KEY is required")

        # Usamos la clase de LangChain que soporta internamente las nuevas APIs
        # task_type se define dinámicamente por defecto en la librería según el contexto
        self._embedder = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=api_key,
        )
        logger.info("EmbeddingService configured with LangChain: %s", model_name)

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Genera embeddings procesando en lotes pequeños."""
        if not texts:
            return []

        all_embeddings = []
        batch_size = 100

        # Procesar en lotes
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            logger.info(
                f"Procesando lote: {i} a {i + len(batch_texts)} de {len(texts)}"
            )

            # Sistema de reintentos exponencial interno para cada lote
            max_retries = 3
            base_delay = 10

            for attempt in range(max_retries):
                try:
                    # En LangChain se usa aembed_documents para lista de textos
                    batch_embeddings = await self._embedder.aembed_documents(
                        batch_texts
                    )
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
                        f"Reintento {attempt + 1}/{max_retries} en {delay}s..."
                    )
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"Error fatal generando embeddings en lote: {e}")
                    raise

            # Pausa entre lotes para no saturar cuota
            if i + batch_size < len(texts):
                await asyncio.sleep(2)

        logger.debug("Generated %d embeddings successfully", len(all_embeddings))
        return cast(list[list[float]], all_embeddings)

    async def embed_query(self, query: str) -> list[float]:
        """Genera embedding para una búsqueda."""
        # Usa aembed_query para queries individuales
        try:
            result = await self._embedder.aembed_query(query)
            return cast(list[float], result)
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return []
