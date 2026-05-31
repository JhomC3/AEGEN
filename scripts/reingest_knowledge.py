#!/usr/bin/env python3
"""
Re-ingiere todo el conocimiento global (storage/knowledge/)
usando SemanticChunker para estructura jerarquica L3->L4.

1. Backup de chunks existentes del archivo
2. Hard-delete chunks existentes
3. Extrae texto (PDF con PyMuPDF, .md/.txt con aiofiles)
4. Ingiere con SemanticChunker (Gemini Flash) para obtener jerarquia
5. Si falla, restaura chunks desde backup (rollback)
"""

import asyncio
import json
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


async def backup_chunks(store: SQLiteStore, filename: str, namespace: str) -> list[dict]:
    """Backup de chunks antes de borrarlos para rollback."""
    db = await store.get_db()
    sql = (
        "SELECT id, chat_id, namespace, content, content_hash, memory_type, "
        "metadata, source_type, confidence, sensitivity, evidence, source_skill "
        "FROM memories WHERE namespace = ? "
        "AND json_extract(metadata, '$.filename') = ?"
    )
    async with db.execute(sql, (namespace, filename)) as cursor:
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "chat_id": row[1],
                "namespace": row[2],
                "content": row[3],
                "content_hash": row[4],
                "memory_type": row[5],
                "metadata": row[6],
                "source_type": row[7],
                "confidence": row[8],
                "sensitivity": row[9],
                "evidence": row[10],
                "source_skill": row[11],
            }
            for row in rows
        ]


async def restore_chunks(store: SQLiteStore, chunks: list[dict]) -> int:
    """Restaura chunks desde backup en caso de fallo."""
    if not chunks:
        return 0
    
    db = await store.get_db()
    restored = 0
    for chunk in chunks:
        try:
            sql = (
                "INSERT INTO memories "
                "(chat_id, namespace, content, content_hash, memory_type, metadata, "
                "source_type, confidence, sensitivity, evidence, source_skill) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            await db.execute(
                sql,
                (
                    chunk["chat_id"],
                    chunk["namespace"],
                    chunk["content"],
                    chunk["content_hash"],
                    chunk["memory_type"],
                    chunk["metadata"],
                    chunk["source_type"],
                    chunk["confidence"],
                    chunk["sensitivity"],
                    chunk["evidence"],
                    chunk["source_skill"],
                ),
            )
            restored += 1
        except Exception as e:
            logger.error("Error restaurando chunk %s: %s", chunk["id"], e)
    
    await db.commit()
    return restored


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

        should_process, reason = loader.should_process_file(file_path)
        if not should_process:
            logger.info("Saltando %s: %s", file_path.name, reason)
            continue

        filename = file_path.name
        logger.info("Procesando: %s", filename)

        try:
            # 1. Backup chunks existentes
            backup = await backup_chunks(store, filename, namespace="global")
            logger.info("  -> %d chunks en backup", len(backup))

            # 2. Hard-delete chunks existentes
            deleted = await store.hard_delete_memories_by_filename(
                filename, namespace="global"
            )
            logger.info("  -> %d chunks anteriores eliminados", deleted)
            total_deleted += deleted

            # 3. Extraer texto
            if file_path.suffix.lower() == ".pdf":
                text = loader.extract_pdf_text(file_path)
            else:
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    text = await f.read()

            if not text or not text.strip():
                logger.warning("  -> Contenido vacio, restaurando backup")
                restored = await restore_chunks(store, backup)
                logger.info("  -> %d chunks restaurados", restored)
                continue

            # 4. Ingerir con SemanticChunker
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
            
            if count == 0:
                logger.warning("  -> No se insertaron chunks, restaurando backup")
                restored = await restore_chunks(store, backup)
                logger.info("  -> %d chunks restaurados", restored)
            else:
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
