# src/memory/global_knowledge_loader.py
import logging
import os
from pathlib import Path

from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


class GlobalKnowledgeLoader:
    """
    Sincroniza el conocimiento base local (/knowledge/) con Google Cloud.
    Asegura que MAGI tenga su 'cerebro' disponible en entornos diskless.
    """

    def __init__(self, knowledge_dir: str = "knowledge"):
        # Detectar entorno Docker para ajustar ruta
        if os.getenv("DOCKER_ENV") == "true":
            self.knowledge_path = Path("/app") / knowledge_dir
        else:
            self.knowledge_path = Path(knowledge_dir)

        logger.info(
            f"GlobalKnowledgeLoader inicializado en: {self.knowledge_path.absolute()}"
        )

    async def sync_knowledge(self):
        """
        Escanea el directorio local y sube archivos faltantes a la nube.
        """
        if not self.knowledge_path.exists():
            logger.warning(
                f"Directorio de conocimiento no encontrado: {self.knowledge_path}"
            )
            return

        # 1. Listar archivos actuales en la nube para evitar duplicados
        cloud_files = await file_search_tool.list_files()
        cloud_names = {f.display_name for f in cloud_files}

        # 2. Escanear locales
        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            # Usamos el prefijo 'knowledge/' para archivos globales
            display_name = f"knowledge/{file_path.name}"

            if display_name in cloud_names:
                logger.debug(f"Conocimiento global ya en nube: {display_name}")
                continue

            logger.info(f"Sincronizando nuevo conocimiento global: {display_name}")
            try:
                await file_search_tool.upload_file(
                    file_path=str(file_path.absolute()),
                    chat_id="knowledge",  # chat_id especial para archivos globales
                    display_name=file_path.name,
                )
            except Exception as e:
                logger.error(f"Error sincronizando {display_name}: {e}")

    async def check_and_bootstrap(self):
        """Hook para ejecutar en el startup de la aplicación."""
        import asyncio

        asyncio.create_task(self.sync_knowledge())


# Singleton
global_knowledge_loader = GlobalKnowledgeLoader()
