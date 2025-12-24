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

    async def get_relevant_files(self, chat_id: str) -> list[Any]:
        """
        Identifica qué archivos son relevantes para este chat.
        Incluye libros generales de TCC y la bóveda específica del usuario.
        """
        all_files = await self.list_files()
        relevant = []
        user_vault_name = f"User_Vault_{chat_id}"
        
        for f in all_files:
            # Incluir libros de TCC (prefijo o nombre)
            if "TCC" in f.display_name.upper() or "TERAPIA" in f.display_name.upper():
                relevant.append(f)
            # Incluir la bóveda del usuario actual
            elif f.display_name == user_vault_name:
                relevant.append(f)
        
        return relevant

    async def query_files(self, query: str, chat_id: str) -> str:
        """
        Realiza una búsqueda semántica en los archivos relevantes (TCC + Usuario).
        Usa la propia capacidad de Gemini para extraer información de los archivos.
        """
        relevant_files = await self.get_relevant_files(chat_id)
        if not relevant_files:
            return ""

        logger.info(f"Realizando consulta RAG en {len(relevant_files)} archivos para {chat_id}")
        
        try:
            # Usamos una instancia ligera del modelo para la extracción
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            
            # Construimos el prompt con los archivos
            prompt_parts = [
                "Actúa como un extractor de información experto.",
                f"Basándote EXCLUSIVAMENTE en los archivos adjuntos, responde a: {query}",
                "Si la información no está en los archivos, di simplemente 'Información no encontrada'.",
                "Sé conciso."
            ]
            # Añadimos los archivos a la lista de partes
            prompt_parts.extend(relevant_files)

            response = model.generate_content(prompt_parts)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error en query_files: {e}")
            return ""

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
