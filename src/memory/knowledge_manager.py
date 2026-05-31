# src/memory/knowledge_manager.py
"""
Gestor de conocimiento global de AEGEN.

Fachada única que orquesta tracking, ingestión y gestión
de archivos de conocimiento (PDFs, MD, TXT) en storage/knowledge/.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import aiofiles

from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.knowledge_tracker import KnowledgeTracker
from src.memory.schemas.knowledge import (
    KnowledgeAddResponse,
    KnowledgeChunker,
    KnowledgeFile,
    KnowledgeStatus,
    KnowledgeStatusResponse,
)
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class KnowledgeManager:
    """
    Fachada única para gestión de conocimiento.

    Responsabilidades:
    - Validar archivos
    - Registrar en tracker
    - Orquestar ingestión
    - Manejar errores y fallbacks
    - Proporcionar visibilidad del estado
    """

    def __init__(
        self,
        store: SQLiteStore,
        tracker: KnowledgeTracker,
        knowledge_dir: Path | str | None = None,
    ) -> None:
        self.store = store
        self.tracker = tracker
        self.pipeline = IngestionPipeline(store)

        if knowledge_dir is None:
            if os.getenv("DOCKER_ENV") == "true":
                knowledge_dir = Path("/app/storage/knowledge")
            else:
                knowledge_dir = Path("storage/knowledge")
        self.knowledge_dir = Path(knowledge_dir)

    async def add_file(
        self,
        file_path: Path,
        chunker: KnowledgeChunker = KnowledgeChunker.SEMANTIC,
    ) -> KnowledgeAddResponse:
        """
        Añade un archivo al sistema de conocimiento.

        Flujo:
        1. Valida archivo (tipo, tamaño)
        2. Calcula hash (dedup)
        3. Copia a storage/knowledge/ si es necesario
        4. Registra en knowledge_files (status=pending)
        5. Ingiera con chunker especificado
        6. Actualiza status=done con chunks generados
        """
        # 1. Validar
        if not file_path.exists():
            return KnowledgeAddResponse(
                success=False, message=f"Archivo no existe: {file_path}"
            )

        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return KnowledgeAddResponse(
                success=False,
                message=f"Tipo no permitido: {ext}. Permitidos: {ALLOWED_EXTENSIONS}",
            )

        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return KnowledgeAddResponse(
                success=False,
                message=f"Archivo muy grande: {file_size} bytes (max: {MAX_FILE_SIZE})",
            )

        # 2. Calcular hash
        file_hash = await self._compute_hash(file_path)

        # 3. Verificar si ya está registrado (dedup)
        existing = await self.tracker.get_by_hash(file_hash)
        if existing and existing.status == KnowledgeStatus.DONE:
            return KnowledgeAddResponse(
                success=False,
                message=f"Archivo ya registrado: {existing.filename}",
                file=existing,
            )

        # 4. Copiar a storage/knowledge/ si no está ahí
        dest_path = self.knowledge_dir / file_path.name
        if not dest_path.exists() or dest_path.resolve() != file_path.resolve():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(file_path, dest_path)
            logger.info("[KNOWLEDGE] Copiado: %s -> %s", file_path.name, dest_path)

        # 5. Registrar en tracker
        if existing:
            knowledge_file = existing
        else:
            knowledge_file = await self.tracker.register_file(
                filename=file_path.name,
                file_hash=file_hash,
                file_size=file_size,
                chunker=chunker,
            )

        # 6. Ingerir
        return await self._ingest_file(knowledge_file, dest_path, chunker)

    async def sync_directory(
        self,
        chunker: KnowledgeChunker = KnowledgeChunker.SEMANTIC,
    ) -> list[KnowledgeAddResponse]:
        """
        Escanea storage/knowledge/ y procesa archivos nuevos.

        Compara hashes para detectar:
        - Archivos nuevos (no en tracker)
        - Archivos modificados (hash diferente)
        """
        if not self.knowledge_dir.exists():
            logger.warning("[KNOWLEDGE] Directorio no existe: %s", self.knowledge_dir)
            return []

        results: list[KnowledgeAddResponse] = []
        tracked_files = {f.filename: f for f in await self.tracker.list_all()}

        for file_path in sorted(self.knowledge_dir.glob("*")):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            filename = file_path.name
            file_hash = await self._compute_hash(file_path)
            file_size = file_path.stat().st_size

            tracked = tracked_files.get(filename)

            if tracked is None:
                # Archivo nuevo
                logger.info("[KNOWLEDGE] Archivo nuevo detectado: %s", filename)
                kf = await self.tracker.register_file(
                    filename=filename,
                    file_hash=file_hash,
                    file_size=file_size,
                    chunker=chunker,
                )
                result = await self._ingest_file(kf, file_path, chunker)
                results.append(result)
            elif tracked.file_hash != file_hash:
                # Archivo modificado
                logger.info("[KNOWLEDGE] Archivo modificado: %s", filename)
                await self._delete_chunks(tracked)
                updated = await self.tracker.update_status(
                    tracked.id, KnowledgeStatus.PENDING
                )
                if updated:
                    result = await self._ingest_file(updated, file_path, chunker)
                    results.append(result)
            # else: sin cambios

        return results

    async def get_status(self) -> KnowledgeStatusResponse:
        """Retorna estado de todos los archivos registrados."""
        files = await self.tracker.list_all()
        total_chunks = await self.tracker.get_total_chunks()
        return KnowledgeStatusResponse(
            total_files=len(files),
            total_chunks=total_chunks,
            files=files,
        )

    async def delete_file(self, filename: str) -> bool:
        """
        Elimina archivo y sus chunks asociados.

        1. Elimina chunks de memories
        2. Elimina registro del tracker
        3. Elimina archivo de storage/knowledge/
        """
        tracked = await self.tracker.get_by_filename(filename)
        if not tracked:
            logger.warning("[KNOWLEDGE] Archivo no encontrado en tracker: %s", filename)
            return False

        # 1. Eliminar chunks
        await self._delete_chunks(tracked)

        # 2. Eliminar del tracker
        await self.tracker.delete(tracked.id)

        # 3. Eliminar archivo físico
        file_path = self.knowledge_dir / filename
        if file_path.exists():
            file_path.unlink()
            logger.info("[KNOWLEDGE] Archivo eliminado: %s", filename)

        return True

    async def reingest_all(
        self,
        chunker: KnowledgeChunker = KnowledgeChunker.SEMANTIC,
    ) -> int:
        """
        Re-ingiere todos los archivos registrados con el chunker especificado.

        Útil para migrar de recursive → semantic.
        Retorna la cantidad de archivos procesados.
        """
        files = await self.tracker.list_all()
        processed = 0

        for kf in files:
            file_path = self.knowledge_dir / kf.filename
            if not file_path.exists():
                logger.warning(
                    "[KNOWLEDGE] Archivo no encontrado en disco: %s", kf.filename
                )
                continue

            # Eliminar chunks viejos
            await self._delete_chunks(kf)

            # Resetear estado
            await self.tracker.update_status(kf.id, KnowledgeStatus.PENDING)

            # Re-ingestar
            await self._ingest_file(kf, file_path, chunker)
            processed += 1

        return processed

    # === Métodos privados ===

    async def _ingest_file(
        self,
        knowledge_file: KnowledgeFile,
        file_path: Path,
        chunker: KnowledgeChunker,
    ) -> KnowledgeAddResponse:
        """Ingiera un archivo y actualiza el tracker."""
        # Marcar como ingesting
        await self.tracker.update_status(knowledge_file.id, KnowledgeStatus.INGESTING)

        try:
            # Extraer texto
            text = await self._extract_text(file_path)
            if not text or not text.strip():
                await self.tracker.update_status(
                    knowledge_file.id,
                    KnowledgeStatus.FAILED,
                    error_message="Contenido vacío",
                )
                return KnowledgeAddResponse(
                    success=False,
                    message=f"Contenido vacío: {file_path.name}",
                    file=knowledge_file,
                )

            # Ingerir con el pipeline
            use_semantic = chunker == KnowledgeChunker.SEMANTIC
            count = await self.pipeline.process_text(
                chat_id="system",
                text=text,
                memory_type="document",
                namespace="global",
                metadata={
                    "filename": file_path.name,
                    "source": "global_knowledge",
                    "source_type": "explicit",
                    "sensitivity": "low",
                },
                source_skill="global_knowledge",
                use_semantic_chunker=use_semantic,
            )

            # Obtener IDs de chunks generados
            chunks_ids = await self._get_chunks_ids(file_path.name)

            # Actualizar tracker
            await self.tracker.update_status(
                knowledge_file.id,
                KnowledgeStatus.DONE,
                chunks_count=count,
                chunks_ids=chunks_ids,
            )

            logger.info(
                "[KNOWLEDGE] Ingerido: %s (%d chunks, %s)",
                file_path.name,
                count,
                chunker.value,
            )

            return KnowledgeAddResponse(
                success=True,
                message=f"Ingerido: {file_path.name} ({count} chunks)",
                file=knowledge_file,
            )

        except Exception as e:
            logger.error("[KNOWLEDGE] Error ingiriendo %s: %s", file_path.name, e)
            await self.tracker.update_status(
                knowledge_file.id,
                KnowledgeStatus.FAILED,
                error_message=str(e),
            )
            return KnowledgeAddResponse(
                success=False,
                message=f"Error: {e}",
                file=knowledge_file,
            )

    async def _extract_text(self, file_path: Path) -> str:
        """Extrae texto de un archivo según su tipo."""
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf_text(file_path)

        async with aiofiles.open(file_path, encoding="utf-8") as f:
            return await f.read()

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extrae texto plano de un PDF usando PyMuPDF."""
        try:
            import fitz

            text = ""
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    text += str(page.get_text())
            return text
        except ImportError:
            logger.error("PyMuPDF (fitz) no instalado.")
            return ""
        except Exception as e:
            logger.error("Error extrayendo texto de %s: %s", pdf_path.name, e)
            return ""

    async def _compute_hash(self, file_path: Path) -> str:
        """Calcula SHA-256 del archivo."""
        sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _get_chunks_ids(self, filename: str) -> list[int]:
        """Obtiene los IDs de chunks asociados a un archivo."""
        db = await self.store.get_db()
        async with db.execute(
            "SELECT id FROM memories WHERE namespace = 'global' "
            "AND json_extract(metadata, '$.filename') = ? "
            "AND is_active = 1",
            (filename,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def _delete_chunks(self, knowledge_file: KnowledgeFile) -> None:
        """Elimina los chunks de un archivo de la tabla memories."""
        if not knowledge_file.chunks_ids:
            # Si no hay IDs, buscar por filename
            chunks_ids = await self._get_chunks_ids(knowledge_file.filename)
        else:
            chunks_ids = knowledge_file.chunks_ids

        if not chunks_ids:
            return

        db = await self.store.get_db()
        placeholders = ",".join(["?"] * len(chunks_ids))
        await db.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})",  # noqa: S608
            chunks_ids,
        )
        await db.commit()

        logger.info(
            "[KNOWLEDGE] Eliminados %d chunks de %s",
            len(chunks_ids),
            knowledge_file.filename,
        )
