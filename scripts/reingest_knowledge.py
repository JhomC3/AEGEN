#!/usr/bin/env python3
"""
Re-ingiere todo el conocimiento global (storage/knowledge/)
usando SemanticChunker para estructura jerarquica L3->L4.

1. Soft-delete chunks existentes del archivo
2. Extrae texto (PDF con PyMuPDF, .md/.txt con aiofiles)
3. Ingiere con SemanticChunker (Gemini Flash) para obtener jerarquia
4. Los viejos chunks quedan inactivos, los nuevos tienen parent_id
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import aiofiles

from src.core.config import settings
from src.memory.global_knowledge_loader import GlobalKnowledgeLoader
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reingest_knowledge")


async def reingest_knowledge() -> None:
    store = SQLiteStore(settings.SQLITE_DB_PATH)
    await store.connect()
    pipeline = IngestionPipeline(store)
    loader = GlobalKnowledgeLoader()

    if not loader.knowledge_path.exists():
        logger.warning(
            "Directorio de conocimiento no encontrado: %s",
            loader.knowledge_path,
        )
        await store.disconnect()
        return

    knowledge_files = sorted(loader.knowledge_path.glob("*"))
    if not knowledge_files:
        logger.info("No hay archivos de conocimiento para procesar.")
        await store.disconnect()
        return

    total_inserted = 0
    total_deleted = 0
    errors = []

    for file_path in knowledge_files:
        if file_path.is_dir() or file_path.name.startswith("."):
            continue

        should_process, reason = loader._should_process_file(file_path)
        if not should_process:
            logger.info("Saltando %s: %s", file_path.name, reason)
            continue

        filename = file_path.name
        logger.info("Procesando: %s", filename)

        try:
            # 1. Hard-delete chunks existentes de este archivo
            deleted = await store.hard_delete_memories_by_filename(
                filename, namespace="global"
            )
            logger.info("  -> %d chunks anteriores eliminados", deleted)
            total_deleted += deleted

            # 2. Extraer texto
            if file_path.suffix.lower() == ".pdf":
                text = loader._extract_pdf_text(file_path)
            else:
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    text = await f.read()

            if not text or not text.strip():
                logger.warning("  -> Contenido vacio, saltando")
                continue

            # 3. Ingerir con SemanticChunker
            count = await pipeline.process_text(
                chat_id="system",
                text=text,
                memory_type="document",
                namespace="global",
                metadata={
                    "filename": filename,
                    "source": "global_knowledge",
                    "source_type": "explicit",
                    "sensitivity": "low",
                },
                source_skill="global_knowledge",
                use_semantic_chunker=True,
            )
            logger.info("  -> %d nuevos chunks insertados", count)
            total_inserted += count

        except Exception as e:
            logger.error("Error procesando %s: %s", filename, e)
            errors.append(filename)
            continue

    logger.info(
        "Re-ingesta completada. "
        "Archivos: %d, "
        "Chunks viejos eliminados: %d, "
        "Nuevos chunks: %d, "
        "Errores: %d",
        len(knowledge_files) - len(errors),
        total_deleted,
        total_inserted,
        len(errors),
    )
    if errors:
        logger.warning("Archivos con error: %s", errors)

    await store.disconnect()


if __name__ == "__main__":
    asyncio.run(reingest_knowledge())
