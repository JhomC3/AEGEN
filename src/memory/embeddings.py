import hashlib
import logging
from typing import Any, cast

import google.generativeai as genai
import numpy as np

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wrapper para el servicio de embeddings de Google con caché persistente en SQLite.
    """

    _configured: bool = False

    def __init__(
        self, model_name: str = "models/gemini-embedding-001", store: Any = None
    ) -> None:
        """Inicializa el cliente de Google GenAI y el almacén SQLite para caché."""
        self.model_name = model_name
        self.store = store

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

    def _get_store(self) -> Any:
        """Obtiene de forma diferida el almacén SQLite si no está provisto."""
        if self.store is None:
            try:
                from src.core.dependencies import get_sqlite_store

                self.store = get_sqlite_store()
            except Exception as e:
                logger.debug(f"SQLiteStore not available dynamically yet: {e}")
        return self.store

    def _hash_text(self, text: str) -> str:
        """Calcula el hash SHA-256 de un texto."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def _get_cached_embedding(self, content_hash: str) -> list[float] | None:
        """Consulta si el embedding ya existe en la base de datos."""
        store = self._get_store()
        if store is None:
            return None

        try:
            db = await store.get_db()
            async with db.execute(
                "SELECT embedding FROM embedding_cache WHERE content_hash = ?",
                (content_hash,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    result: list[float] = np.frombuffer(
                        row[0], dtype=np.float32
                    ).tolist()
                    return result
        except Exception as e:
            logger.warning(f"Error reading embedding cache: {e}")
        return None

    async def _save_cached_embedding(
        self, content_hash: str, embedding: list[float]
    ) -> None:
        """Guarda un nuevo embedding en la base de datos."""
        store = self._get_store()
        if store is None:
            return

        try:
            embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
            db = await store.get_db()
            await db.execute(
                "INSERT OR IGNORE INTO embedding_cache (content_hash, embedding) VALUES (?, ?)",
                (content_hash, embedding_blob),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Error saving to embedding cache: {e}")

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Genera embeddings para una lista de textos aprovechando la caché."""
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        hashes: list[str] = [self._hash_text(t) for t in texts]

        # 1. Intentar resolver de caché primero
        for i, h in enumerate(hashes):
            cached = await self._get_cached_embedding(h)
            if cached is not None:
                results[i] = cached

        # 2. Identificar textos faltantes
        miss_indices = [i for i, r in enumerate(results) if r is None]
        if miss_indices:
            miss_texts = [texts[idx] for idx in miss_indices]
            try:
                # SDK sincrónico
                response = genai.embed_content(
                    model=self.model_name,
                    content=miss_texts,
                    task_type=task_type,
                    output_dimensionality=768,
                )

                embeddings = response.get("embedding", [])
                logger.debug("Generated %d embeddings from API", len(embeddings))

                # 3. Guardar en caché y rellenar resultados
                for idx, embedding in zip(miss_indices, embeddings, strict=False):
                    emb_list = cast(list[float], embedding)
                    results[idx] = emb_list
                    await self._save_cached_embedding(hashes[idx], emb_list)

            except Exception as e:
                logger.error("Error generating embeddings from API: %s", e)
                raise

        return cast(list[list[float]], results)

    async def embed_query(self, query: str) -> list[float]:
        """Genera embedding para una búsqueda."""
        embeddings = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else []
