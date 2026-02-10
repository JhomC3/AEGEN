# src/memory/ingestion_pipeline.py
"""
Ingestion pipeline for processing and storing memories.

Orchestrates Chunker, Deduplicator, EmbeddingService, and SQLiteStore.
"""

import logging

from src.memory.chunker import RecursiveChunker
from src.memory.deduplicator import Deduplicator
from src.memory.embeddings import EmbeddingService
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orquestador del pipeline de ingestión de memoria.
    """

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.chunker = RecursiveChunker()
        self.deduplicator = Deduplicator()
        self.embedding_service = EmbeddingService()

    async def process_text(
        self,
        chat_id: str,
        text: str,
        memory_type: str = "conversation",
        namespace: str = "user",
        metadata: dict | None = None,
    ) -> int:
        """
        Procesa un texto completo: chunking -> dedupe -> embedding -> storage.

        Args:
            chat_id: ID del chat
            text: Texto a procesar
            memory_type: Tipo de memoria (fact, preference, etc.)
            namespace: Espacio de nombres
            metadata: Metadatos base

        Returns:
            Número de fragmentos nuevos insertados.
        """
        if not text or not text.strip():
            return 0

        metadata = metadata or {}

        # 1. Chunking
        chunks = self.chunker.chunk(text, metadata)
        if not chunks:
            return 0

        new_chunks_count = 0

        # 2. Filtrar duplicados y preparar para inserción
        to_embed = []
        for chunk in chunks:
            content_hash = self.deduplicator.generate_hash(chunk.content)

            # Verificar si ya existe en la DB
            if not await self.store.hash_exists(content_hash):
                to_embed.append((chunk, content_hash))
            else:
                logger.debug(f"Skipping duplicate chunk with hash {content_hash}")

        if not to_embed:
            return 0

        # 3. Batch Embedding
        texts_to_embed = [item[0].content for item in to_embed]
        embeddings = await self.embedding_service.embed_texts(texts_to_embed)

        # 4. Storage
        for (chunk, content_hash), embedding in zip(to_embed, embeddings, strict=False):
            try:
                # Insertar memoria de texto
                memory_id = await self.store.insert_memory(
                    chat_id=chat_id,
                    content=chunk.content,
                    content_hash=content_hash,
                    memory_type=memory_type,
                    namespace=namespace,
                    metadata=chunk.metadata,
                )

                # Insertar vector
                if memory_id != -1:
                    await self.store.insert_vector(memory_id, embedding)
                    new_chunks_count += 1

            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                continue

        logger.info(f"Ingested {new_chunks_count} new chunks for chat {chat_id}")
        return new_chunks_count
