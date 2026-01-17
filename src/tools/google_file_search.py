# src/tools/google_file_search.py
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from google import genai
from src.core.config import settings

logger = logging.getLogger(__name__)

class GoogleFileSearchTool:
    """
    Herramienta para gestionar y buscar información en archivos usando la Google File API.
    Implementa un sistema de Managed RAG (Búsqueda de archivos gestionada) para Gemini.
    Migrado al nuevo SDK 'google-genai' para compatibilidad con Gemini 2.x.
    """

    def __init__(self):
        api_key = settings.GOOGLE_API_KEY.get_secret_value() if settings.GOOGLE_API_KEY else ""
        self.client = genai.Client(api_key=api_key)
        self._file_cache = None
        self._last_cache_update = 0
        self.CACHE_TTL = 300  # 5 minutos
        logger.info("GoogleFileSearchTool inicializada con el NUEVO SDK google-genai.")

    async def list_files(self):
        """
        Lista los archivos disponibles en la File API con cache.
        """
        current_time = time.time()
        if self._file_cache and (current_time - self._last_cache_update < self.CACHE_TTL):
            return self._file_cache
            
        try:
            # El nuevo SDK usa client.files.list() y devuelve un generador
            files = list(self.client.files.list())
            self._file_cache = files
            self._last_cache_update = current_time
            return files
        except Exception as e:
            logger.error(f"Error listando archivos con el nuevo SDK: {e}")
            return self._file_cache or []

    async def upload_file(self, file_path: str, display_name: Optional[str] = None):
        """
        Sube un archivo a la Google File API.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
                
            name = display_name or path.name
            logger.info(f"Subiendo archivo {path.name} como '{name}'...")
            
            # El nuevo SDK usa client.files.upload()
            uploaded_file = self.client.files.upload(path=file_path, config={'display_name': name})
            
            self._file_cache = None # Invalidar cache
            logger.info(f"Archivo subido exitosamente: {uploaded_file.uri}")
            return uploaded_file
        except Exception as e:
            logger.error(f"Error subiendo archivo {file_path}: {e}")
            raise

    async def get_relevant_files(self, chat_id: str, tags: Optional[list[str]] = None) -> list[Any]:
        """
        Identifica qué archivos son relevantes basado en chat_id y tags opcionales.
        """
        all_files = await self.list_files()
        relevant = []
        user_vault_name = f"User_Vault_{chat_id}"
        
        tags_upper = [t.upper() for t in (tags or [])]
        
        for f in all_files:
            f_name_upper = f.display_name.upper()
            
            # 1. CORE KERNEL
            if "CORE" in f_name_upper or "STOIC" in f_name_upper:
                relevant.append(f)
                continue
                
            # 2. TAG MATCH
            if tags_upper and any(tag in f_name_upper for tag in tags_upper):
                relevant.append(f)
                continue

            # 3. USER VAULT
            if f.display_name == user_vault_name:
                relevant.append(f)
        
        # En el nuevo SDK, el estado es un string directo o un enum. Comparar con string es seguro.
        active_files = [f for f in relevant if f.state == "ACTIVE"]
        if len(relevant) > len(active_files):
            logger.warning(f"Omitiendo {len(relevant) - len(active_files)} archivos en estado no-ACTIVE")
            
        return active_files[:5]

    async def query_files(self, query: str, chat_id: str, tags: Optional[list[str]] = None) -> str:
        """
        Realiza búsqueda semántica inteligente (Smart RAG) en archivos relevantes.
        """
        relevant_files = await self.get_relevant_files(chat_id, tags)
        if not relevant_files:
            logger.info(f"No hay archivos relevantes para {chat_id} con tags {tags}")
            return ""

        logger.info(f"Smart RAG: Consultando {len(relevant_files)} archivos para {chat_id} (Tags: {tags})")
        
        try:
            model_name = settings.DEFAULT_LLM_MODEL
            # Quitar prefijo 'models/' si existe, el nuevo SDK lo maneja o prefiere el ID puro
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")
            
            logger.info(f"Smart RAG: Usando modelo {model_name} con el nuevo SDK.")
            
            instruction = (
                "Actúa como un extractor de sabiduría estoica y técnica.\n"
                f"Basándote EXCLUSIVAMENTE en los archivos adjuntos, responde de forma concisa: {query}\n"
                "Si la información no está, di 'Información no encontrada'.\n"
                "Estilo: Directo, sin introducciones innecesarias."
            )
            
            # El orden recomendado ahora es [archivo, ..., instrucción]
            contents = relevant_files + [instruction]

            # El nuevo SDK soporta llamadas async directamente si el método termina en _async o similar?
            # En google-genai, se usa client.models.generate_content (sincrónico)
            # Para async, se usa el cliente asíncrono o run_in_executor.
            # Sin embargo, el SDK tiene un diseño robusto. Probemos sincrónico primero o busquemos el async.
            # Según doc: client.models.generate_content es bloqueante.
            
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=contents
            )
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error en Smart RAG query_files (nuevo SDK): {e}", exc_info=True)
            return ""

    async def delete_file(self, file_name: str):
        """Elimina un archivo de la File API."""
        try:
            self.client.files.delete(name=file_name)
            logger.info(f"Archivo eliminado: {file_name}")
            self._file_cache = None # Reset cache
        except Exception as e:
            logger.error(f"Error eliminando archivo con el nuevo SDK: {e}")

# Instancia singleton
file_search_tool = GoogleFileSearchTool()
