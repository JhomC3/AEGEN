# src/memory/global_knowledge_loader.py
import logging
import os
from pathlib import Path

import aiofiles

from src.memory.vector_memory_manager import MemoryType, VectorMemoryManager

logger = logging.getLogger(__name__)


class GlobalKnowledgeLoader:
    """
    Sincroniza el conocimiento base local (/knowledge/) con SQLite (Local-First).
    Asegura que MAGI tenga su 'cerebro' disponible.
    """

    def __init__(self, knowledge_dir: str = "knowledge"):
        # Detectar entorno Docker para ajustar ruta
        if os.getenv("DOCKER_ENV") == "true":
            self.knowledge_path = Path("/app") / knowledge_dir
        else:
            self.knowledge_path = Path(knowledge_dir)

        self.manager = VectorMemoryManager()
        logger.info(
            f"GlobalKnowledgeLoader inicializado en: {self.knowledge_path.absolute()}"
        )

    async def sync_knowledge(self):
        """
        Escanea el directorio local e ingiere archivos nuevos en SQLite.
        """
        if not self.knowledge_path.exists():
            logger.warning(
                f"Directorio de conocimiento no encontrado: {self.knowledge_path}"
            )
            return

        # 2. Escanear locales
        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            logger.info(f"Procesando conocimiento global: {file_path.name}")
            try:
                # Leer contenido del archivo de forma asíncrona
                async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                    content = await f.read()

                # Ingerir en SQLite con namespace global
                new_chunks = await self.manager.store_context(
                    user_id="system",  # ID especial para global
                    content=content,
                    context_type=MemoryType.DOCUMENT,
                    metadata={"filename": file_path.name, "source": "global_knowledge"},
                    namespace="global",
                )

                if new_chunks > 0:
                    logger.info(
                        f"Ingeridos {new_chunks} fragmentos nuevos de {file_path.name}"
                    )
                else:
                    logger.debug(
                        f"Conocimiento global {file_path.name} ya estaba actualizado."
                    )

            except Exception as e:
                logger.error(f"Error sincronizando {file_path.name}: {e}")

    async def check_and_bootstrap(self):
        """Hook para ejecutar en el startup de la aplicación."""
        await self.sync_knowledge()


# Singleton
global_knowledge_loader = GlobalKnowledgeLoader()
