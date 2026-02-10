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

    async def sync_knowledge(self):
        """
        Escanea el directorio de storage e ingiere archivos nuevos en SQLite.
        """
        if not self.knowledge_path.exists():
            logger.warning(
                f"Directorio de conocimiento no encontrado: {self.knowledge_path}. "
                "Asegúrese de que existan archivos en storage/knowledge/"
            )
            # Depuración: Listar contenido del padre para ver qué está montado
            try:
                parent = self.knowledge_path.parent
                if parent.exists():
                    logger.info(
                        f"Contenido de {parent}: {[x.name for x in parent.glob('*')]}"
                    )
                else:
                    logger.warning(f"El directorio padre {parent} tampoco existe.")
            except Exception as e:
                logger.error(f"Error listando directorio: {e}")
            return

        # 2. Escanear archivos locales
        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            logger.info(f"Procesando conocimiento global: {file_path.name}")
            try:
                content = ""
                # Manejo según extensión
                if file_path.suffix.lower() == ".pdf":
                    content = self._extract_pdf_text(file_path)
                else:
                    # Leer archivos de texto como UTF-8
                    async with aiofiles.open(
                        file_path, mode="r", encoding="utf-8"
                    ) as f:
                        content = await f.read()

                if not content or not content.strip():
                    logger.warning(f"No se pudo extraer contenido de {file_path.name}")
                    continue

                # Ingerir en SQLite con namespace global
                # El manager internamente usará el pipeline que ya verifica deduplicación por hash
                new_chunks = await self.manager.store_context(
                    user_id="system",
                    content=content,
                    context_type=MemoryType.DOCUMENT,
                    metadata={"filename": file_path.name, "source": "global_knowledge"},
                    namespace="global",
                )

                if new_chunks > 0:
                    logger.info(
                        f"✅ Ingeridos {new_chunks} fragmentos nuevos de {file_path.name}"
                    )
                else:
                    logger.info(
                        f"ℹ️ Conocimiento global {file_path.name} ya está al día en la base de datos."
                    )

            except Exception as e:
                logger.error(f"Error sincronizando {file_path.name}: {e}")

    async def check_and_bootstrap(self):
        """Hook para ejecutar en el startup de la aplicación."""
        await self.sync_knowledge()


# Singleton
global_knowledge_loader = GlobalKnowledgeLoader()
