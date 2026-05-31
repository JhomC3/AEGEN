# src/memory/ingestion_pipeline.py
"""
Ingestion pipeline for processing and storing memories.

Orchestrates Chunker, Deduplicator, EmbeddingService, and SQLiteStore.
"""

import logging
from datetime import UTC, datetime

from src.memory.chunker import RecursiveChunker
from src.memory.deduplicator import Deduplicator
from src.memory.embeddings import EmbeddingService
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _enrich_temporal_metadata(metadata: dict) -> dict:
    """Añade campos temporales derivados de created_at al metadata."""
    now = datetime.now(UTC)
    ts = datetime.fromisoformat(metadata.get("created_at", now.isoformat()))
    metadata["day_of_week"] = ts.weekday()
    metadata["hour_of_day"] = ts.hour
    metadata["week_of_year"] = ts.isocalendar()[1]
    metadata["is_weekend"] = ts.weekday() >= 5
    return metadata


class IngestionPipeline:
    """
    Orquestador del pipeline de ingestión de memoria.
    """

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.chunker = RecursiveChunker()
        self.deduplicator = Deduplicator()
        self.embedding_service = EmbeddingService()

    async def process_text(  # noqa: C901
        self,
        chat_id: str,
        text: str,
        memory_type: str = "conversation",
        namespace: str | None = None,
        metadata: dict | None = None,
        source_skill: str | None = None,
        use_semantic_chunker: bool = False,
    ) -> int:
        """
        Procesa un texto completo: chunking -> dedupe -> embedding -> storage.

        Args:
            chat_id: ID del chat
            text: Texto a procesar
            memory_type: Tipo de memoria (fact, preference, etc.)
            namespace: Espacio de nombres (se calcula como 'user_{chat_id}' por defecto para usuarios)
            metadata: Metadatos base
            source_skill: Skill origen que generó esta memoria
            use_semantic_chunker: True si se debe usar segmentación semántica jerárquica (libros, YouTube)

        Returns:
            Número de fragmentos nuevos insertados.
        """
        if not text or not text.strip():
            return 0

        # Namespace legacy "user" aún válido; nuevos registros usan "user_{chat_id}"
        if namespace is None or namespace == "user":
            final_namespace = f"user_{chat_id}"
        else:
            final_namespace = namespace

        metadata = metadata or {}
        metadata = _enrich_temporal_metadata(metadata)

        # Branch A: Ingesta Jerárquica Semántica (Pilar I) (Fase 3, Tarea 3.6)
        if use_semantic_chunker:
            try:
                from src.memory.semantic_chunker import SemanticChunker

                chunker = SemanticChunker()

                # Ejecuta segmentación y purificación de Gemini
                flat_structures = await chunker.chunk_semantically(text)
                if not flat_structures:
                    logger.warning(
                        "[INGESTION] Semantic chunker returned empty structures. Fallback to Recursive."
                    )
                else:
                    return await self._process_semantic_structures(
                        chat_id,
                        flat_structures,
                        final_namespace,
                        source_skill,
                        metadata,
                    )
            except Exception as se:
                logger.error(
                    f"[INGESTION] Failed semantic chunker execution: {se}. Fallback to Recursive.",
                    exc_info=True,
                )

        # Branch B: Chunker Recursivo tradicional (fallback para global o default para user)
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
                # Extract provenance from chunk metadata (if provided)
                chunk_meta = chunk.metadata or {}
                provenance = {
                    k: chunk_meta.pop(k)
                    for k in ("source_type", "confidence", "sensitivity", "evidence")
                    if k in chunk_meta
                }

                # Propagar source_skill si está provisto
                final_source_skill = source_skill or chunk_meta.pop(
                    "source_skill", None
                )

                # Insertar memoria de texto
                memory_id = await self.store.insert_memory(
                    chat_id=chat_id,
                    content=chunk.content,
                    content_hash=content_hash,
                    memory_type=memory_type,
                    namespace=final_namespace,
                    metadata=chunk_meta,
                    source_skill=final_source_skill,
                    **provenance,
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

    async def _process_semantic_structures(  # noqa: C901
        self,
        chat_id: str,
        structures: list[dict],
        namespace: str,
        source_skill: str | None,
        base_metadata: dict,
    ) -> int:
        """
        Procesa e ingesta la ontología jerárquica: Chunks Padres (Nivel 3)
        y Chunks Hijos (Nivel 4) con su respectiva relación jerárquica (parent_id).
        """
        ingested_count = 0

        for parent_data in structures:
            # 1. Ingestar el Padre (Nivel 3)
            parent_content = parent_data["content"]
            parent_domain = parent_data["domain"]
            parent_hash = self.deduplicator.generate_hash(parent_content)

            # Chequear duplicidad del padre
            if await self.store.hash_exists(parent_hash):
                # Si existe, recuperamos su ID
                db = await self.store.get_db()
                async with db.execute(
                    "SELECT id FROM memories WHERE content_hash = ?", (parent_hash,)
                ) as cursor:
                    row = await cursor.fetchone()
                    parent_id = row[0] if row else -1
            else:
                meta = {
                    **base_metadata,
                    "domain": parent_domain,
                    "hierarchy_level": 3,
                }
                parent_id = await self.store.insert_memory(
                    chat_id=chat_id,
                    content=parent_content,
                    content_hash=parent_hash,
                    memory_type="document_parent",  # tipo de persistencia padre
                    namespace=namespace,
                    metadata=meta,
                    source_skill=source_skill,
                    confidence=1.0,
                    source_type="explicit",
                )
                if parent_id != -1:
                    ingested_count += 1

            if parent_id == -1:
                continue

            # 2. Ingestar Hijos (Nivel 4) con relación parent_id y vectorizar
            children = parent_data.get("children", [])
            if not children:
                continue

            # Filtrar duplicidad en hijos antes de vectorizar
            children_to_embed = []
            for child in children:
                child_content = child["content"]
                child_hash = self.deduplicator.generate_hash(child_content)
                if not await self.store.hash_exists(child_hash):
                    children_to_embed.append((child, child_hash))

            if not children_to_embed:
                continue

            # Batch embedding de los hijos
            child_texts = [item[0]["content"] for item in children_to_embed]
            embeddings = await self.embedding_service.embed_texts(child_texts)

            for (child, child_hash), embedding in zip(
                children_to_embed, embeddings, strict=False
            ):
                meta = {
                    **base_metadata,
                    "domain": child["domain"],
                    "hierarchy_level": 4,
                }

                # Insertamos con el parent_id resuelto (jerarquía vertical Parent-Child RAG)
                child_id = await self.store.insert_memory(
                    chat_id=chat_id,
                    content=child["content"],
                    content_hash=child_hash,
                    memory_type="document",
                    namespace=namespace,
                    metadata=meta,
                    source_skill=source_skill,
                    parent_id=parent_id,  # Link jerárquico Padre-Hijo
                    confidence=1.0,
                    source_type="explicit",
                )

                if child_id != -1:
                    await self.store.insert_vector(child_id, embedding)
                    ingested_count += 1

        logger.info(
            f"[INGESTION] Hierarchical semantic ingestion complete. Inserted: {ingested_count} records."
        )
        return ingested_count
