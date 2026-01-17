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
        self._file_cache = None
        self._last_cache_update = 0
        self.CACHE_TTL = 300  # 5 minutos
        logger.info("GoogleFileSearchTool inicializada con Smart RAG support.")

    async def list_files(self):
        """
        Lista los archivos disponibles en la File API con cache.
        """
        current_time = time.time()
        if self._file_cache and (current_time - self._last_cache_update < self.CACHE_TTL):
            return self._file_cache
            
        try:
            files = list(genai.list_files())
            self._file_cache = files
            self._last_cache_update = current_time
            return files
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            return self._file_cache or []

    async def upload_file(self, file_path: str, display_name: Optional[str] = None):
        """
        Sube un archivo a la Google File API.
        
        Args:
            file_path: Ruta local del archivo.
            display_name: Nombre opcional para mostrar en la API.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
                
            name = display_name or path.name
            logger.info(f"Subiendo archivo {path.name} como '{name}'...")
            
            # Sincrónico en el SDK, pero lo envolvemos si fuera necesario. 
            # Por ahora uso directo ya que la mayoría de scripts son async.
            uploaded_file = genai.upload_file(path=str(path), display_name=name)
            
            # Esperar a que el archivo pase de 'PROCESSING' a 'ACTIVE' (opcional pero recomendado)
            # Para subidas masivas en scripts, es mejor dejar que el script maneje la espera
            # o simplemente invalidar cache y listo.
            
            self._file_cache = None # Invalidar cache para forzar recarga en la próxima consulta
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
            
            # 1. CORE KERNEL: Archivos marcados como CORE o ESTOICO siempre incluidos
            if "CORE" in f_name_upper or "STOIC" in f_name_upper:
                relevant.append(f)
                continue
                
            # 2. TAG MATCH: Si tiene tags, priorizar archivos que los contengan
            if tags_upper and any(tag in f_name_upper for tag in tags_upper):
                relevant.append(f)
                continue

            # 3. USER VAULT: Bóveda específica del usuario
            if f.display_name == user_vault_name:
                relevant.append(f)
        
        # Limitar número de archivos y asegurar que estén ACTIVE
        active_files = [f for f in relevant if f.state.name == "ACTIVE"]
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
            # Forzamos 1.5-flash para RAG por estabilidad con el File API y evitar errores 400
            model_name = "models/gemini-1.5-flash"
            
            logger.info(f"Smart RAG: Usando modelo {model_name} para consulta de archivos.")
            model = genai.GenerativeModel(model_name)
            
            prompt_parts = [
                "Actúa como un extractor de sabiduría estoica y técnica.",
                f"Basándote EXCLUSIVAMENTE en los archivos adjuntos, responde de forma concisa: {query}",
                "Si la información no está, di 'Información no encontrada'.",
                "Estilo: Directo, sin introducciones innecesarias."
            ]
            
            # Solo añadir archivos que existan y sean válidos
            prompt_parts.extend(relevant_files)

            logger.debug(f"Smart RAG Prompt Parts: {[str(p) if not hasattr(p, 'name') else p.name for p in prompt_parts]}")
            
            response = model.generate_content(prompt_parts)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error en Smart RAG query_files: {e}", exc_info=True)
            return ""

    async def delete_file(self, file_name: str):
        """Elimina un archivo de la File API."""
        try:
            genai.delete_file(file_name)
            logger.info(f"Archivo eliminado: {file_name}")
            self._file_cache = None # Reset cache
        except Exception as e:
            logger.error(f"Error eliminando archivo: {e}")

# Instancia singleton
file_search_tool = GoogleFileSearchTool()
