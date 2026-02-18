# src/memory/global_knowledge_loader.py
import logging
import os
from pathlib import Path

import aiofiles

from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class GlobalKnowledgeLoader:
    """
    Sincroniza el conocimiento base especializado con SQLite.
    """

    def __init__(self, knowledge_dir: str = "storage/knowledge") -> None:
        # Detectar entorno Docker para ajustar ruta
        if os.getenv("DOCKER_ENV") == "true":
            self.knowledge_path = Path("/app") / knowledge_dir
        else:
            self.knowledge_path = Path(knowledge_dir)

        self._manager: VectorMemoryManager | None = None
        logger.info(
            "GlobalKnowledgeLoader inicializado en: %s", self.knowledge_path.absolute()
        )

    @property
    def manager(self) -> VectorMemoryManager:
        """Lazy load del gestor de memoria."""
        if self._manager is None:
            from src.core.dependencies import get_vector_memory_manager

            self._manager = get_vector_memory_manager()
        return self._manager

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
            logger.error("PyMuPDF (fitz) no instalado. No se puede procesar PDF.")
            return ""
        except Exception as e:
            logger.error("Error extrayendo texto de PDF %s: %s", pdf_path.name, e)
            return ""

    def _should_process_file(self, file_path: Path) -> tuple[bool, str]:
        """Determina si un archivo debe ser procesado."""
        import re

        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        if ext not in (".pdf", ".md", ".txt"):
            return False, f"extension_no_permitida: {ext}"

        is_core = name.startswith("core_")
        if not is_core and re.search(r"\d{5,}", name):
            return False, "posible_id_usuario_detectado"

        ignore_keywords = ("buffer", "summary", "vault", "profile")
        for kw in ignore_keywords:
            if kw in name:
                return False, f"keyword_personal_legacy: {kw}"

        return True, "aceptado"

    async def ingest_file(self, file_path: Path) -> int:
        """Ingiere un archivo individual en el sistema de memoria."""
        logger.info("Procesando conocimiento global: %s", file_path.name)
        try:
            content = ""
            if file_path.suffix.lower() == ".pdf":
                content = self._extract_pdf_text(file_path)
            else:
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    content = await f.read()

            if not content or not content.strip():
                logger.warning("No se pudo extraer contenido de %s", file_path.name)
                return 0

            return await self.manager.store_context(
                user_id="system",
                content=content,
                context_type=MemoryType.DOCUMENT,
                metadata={
                    "filename": file_path.name,
                    "source": "global_knowledge",
                    "source_type": "explicit",
                    "sensitivity": "low",
                },
                namespace="global",
            )
        except Exception as e:
            logger.error("Error sincronizando %s: %s", file_path.name, e)
            return 0

    async def sync_knowledge(self) -> None:
        """Escanea e ingiere archivos nuevos en SQLite."""
        if not self.knowledge_path.exists():
            logger.info(
                "Directorio de conocimiento no encontrado: %s. "
                "Saltando sincronización global.",
                self.knowledge_path.absolute(),
            )
            return

        processed_count = 0
        skipped_count = 0

        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            should_process, reason = self._should_process_file(file_path)
            if not should_process:
                logger.info(
                    "[INGESTA] Archivo descartado: %s | Razón: %s",
                    file_path.name,
                    reason,
                )
                skipped_count += 1
                continue

            await self.ingest_file(file_path)
            processed_count += 1

        logger.info(
            "Sincronización finalizada. Procesados: %d, Saltados: %d",
            processed_count,
            skipped_count,
        )

    async def check_and_bootstrap(self) -> None:
        """Hook para ejecutar en el startup de la aplicación."""
        logger.info("Iniciando sincronización de conocimiento en segundo plano...")
        await self.sync_knowledge()
        logger.info("Sincronización de conocimiento global completada.")


# Singleton
global_knowledge_loader = GlobalKnowledgeLoader()
