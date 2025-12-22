# src/tools/google_file_search.py
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import google.generativeai as genai
from src.core.config import settings

logger = logging.getLogger(__name__)

class GoogleFileSearchTool:
    """
    Herramienta para gestionar y buscar información en archivos usando la Google File API.
    Implementa un sistema de Managed RAG (Búsqueda de archivos gestionada) para Gemini.
    """

    def __init__(self):
        api_key = settings.GOOGLE_API_KEY.get_secret_value() if settings.GOOGLE_API_KEY else ""
        genai.configure(api_key=api_key)
        logger.info("GoogleFileSearchTool inicializada.")

    async def upload_file(self, file_path: str, display_name: Optional[str] = None) -> Any:
        """
        Sube un archivo a la Google File API.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        logger.info(f"Subiendo archivo a Google File API: {path.name}...")
        try:
            sample_file = genai.upload_file(path=str(path), display_name=display_name or path.name)
            
            # Esperar a que el archivo sea procesado si es necesario (para algunos tipos)
            # Generalmente es inmediato para texto/pdf
            logger.info(f"Archivo subido con éxito: {sample_file.uri}")
            return sample_file
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            raise

    async def list_files(self):
        """
        Lista los archivos disponibles en la File API.
        """
        return list(genai.list_files())

    async def delete_file(self, file_name: str):
        """
        Elimina un archivo de la File API.
        """
        genai.delete_file(file_name)
        logger.info(f"Archivo eliminado: {file_name}")

    async def get_search_context(self, query: str, file_uris: list[str]) -> str:
        """
        Busca información específica dentro de una lista de archivos.
        Nota: Esto usa la capacidad de la ventana de contexto de Gemini para 'leer' los archivos.
        """
        # Esta función será consumida por el Orquestador o el ChatAgent
        # para inyectar contenido de archivos en el prompt.
        pass

# Instancia singleton
file_search_tool = GoogleFileSearchTool()
