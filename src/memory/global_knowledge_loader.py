# src/memory/global_knowledge_loader.py
import logging
import os
from pathlib import Path

import aiofiles

from src.memory.vector_memory_manager import MemoryType

logger = logging.getLogger(__name__)


class GlobalKnowledgeLoader:
    """
    Sincroniza el conocimiento base especializado (storage/knowledge/) con SQLite.
    Soporta archivos de texto y PDFs binariamente.
    """

    def __init__(self, knowledge_dir: str = "storage/knowledge"):
        # Detectar entorno Docker para ajustar ruta
        if os.getenv("DOCKER_ENV") == "true":
            self.knowledge_path = Path("/app") / knowledge_dir
        else:
            self.knowledge_path = Path(knowledge_dir)

        self._manager = None
        logger.info(
            f"GlobalKnowledgeLoader inicializado en: {self.knowledge_path.absolute()}"
        )

    @property
    def manager(self):
        """Lazy load del gestor de memoria para usar el singleton global."""
        if self._manager is None:
            from src.core.dependencies import get_vector_memory_manager

            self._manager = get_vector_memory_manager()
        return self._manager

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """
        Extrae texto plano de un PDF usando PyMuPDF (fitz).
        """
        try:
            import fitz  # PyMuPDF

            text = ""
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        except ImportError:
            logger.error("PyMuPDF (fitz) no está instalado. No se puede procesar PDF.")
            return ""
        except Exception as e:
            logger.error(f"Error extrayendo texto de PDF {pdf_path.name}: {e}")
            return ""

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Determina si un archivo debe ser procesado como conocimiento global.
        Filtra extensiones permitidas e ignora archivos personales/legacy.
        """
        import re

        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        # 1. Solo permitir PDF, Markdown y Texto
        if ext not in (".pdf", ".md", ".txt"):
            return False

        # 2. Ignorar archivos con IDs de usuario (números largos)
        if re.search(r"\d{5,}", name):
            return False

        # 3. Ignorar palabras clave de archivos personales legacy
        ignore_keywords = ("buffer", "summary", "vault", "profile")
        if any(kw in name for kw in ignore_keywords):
            return False

        return True

    async def sync_knowledge(self):
        """
        Escanea el directorio de storage e ingiere archivos nuevos en SQLite.
        Aplica filtros de seguridad para evitar contaminar el namespace global.
        """
        if not self.knowledge_path.exists():
            logger.info(
                f"Directorio de conocimiento no encontrado: {self.knowledge_path.absolute()}. "
                "Saltando sincronización global."
            )
            return

        # 2. Escanear archivos locales
        processed_count = 0
        skipped_count = 0

        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            if not self._should_process_file(file_path):
                logger.debug(f"Saltando archivo no global/legacy: {file_path.name}")
                skipped_count += 1
                continue

            logger.info(f"Procesando conocimiento global: {file_path.name}")
            try:
                content = ""
                # Manejo según extensión
                if file_path.suffix.lower() == ".pdf":
                    content = self._extract_pdf_text(file_path)
                else:
                    # Leer archivos de texto como UTF-8
                    async with aiofiles.open(file_path, encoding="utf-8") as f:
                        content = await f.read()

                if not content or not content.strip():
                    logger.warning(f"No se pudo extraer contenido de {file_path.name}")
                    continue

                # Ingerir en SQLite con namespace global
                new_chunks = await self.manager.store_context(
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

                if new_chunks > 0:
                    logger.info(
                        f"✅ Ingeridos {new_chunks} fragmentos nuevos de {file_path.name}"
                    )
                else:
                    logger.debug(f"ℹ️ {file_path.name} ya está sincronizado.")
                processed_count += 1

            except Exception as e:
                logger.error(f"Error sincronizando {file_path.name}: {e}")

        logger.info(
            f"Sincronización finalizada. Procesados: {processed_count}, Saltados: {skipped_count}"
        )

    async def check_and_bootstrap(self):
        """Hook para ejecutar en el startup de la aplicación."""
        logger.info("Iniciando sincronización de conocimiento en segundo plano...")
        await self.sync_knowledge()
        logger.info("Sincronización de conocimiento global completada.")


# Singleton
global_knowledge_loader = GlobalKnowledgeLoader()
