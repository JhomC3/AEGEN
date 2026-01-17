import logging
import os
import time
import asyncio
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types
from src.core.config import settings

logger = logging.getLogger(__name__)

class GoogleFileSearchTool:
    """
    Herramienta para gestionar y buscar información en archivos usando la Google File API.
    Implementa un sistema de Managed RAG (Búsqueda de archivos gestionada) para Gemini.
    Migrado al nuevo SDK 'google-genai' para compatibilidad con Gemini 2.x.
    Refactorizado para cumplir estrictamente con los contratos de API y Best Practices.
    """

    def __init__(self):
        api_key = settings.GOOGLE_API_KEY.get_secret_value() if settings.GOOGLE_API_KEY else ""
        self.client = genai.Client(api_key=api_key)
        self._file_cache = None
        self._last_cache_update = 0
        self.CACHE_TTL = 300  # 5 minutos
        logger.info(f"GoogleFileSearchTool inicializada. SDK google.genai version: {getattr(genai, '__version__', 'unknown')}")

    async def list_files(self):
        """
        Lista los archivos disponibles en la File API con cache.
        """
        current_time = time.time()
        if self._file_cache and (current_time - self._last_cache_update < self.CACHE_TTL):
            return self._file_cache
            
        try:
            # Ejecutamos la llamada síncrona en un thread para no bloquear el loop
            files = await asyncio.to_thread(lambda: list(self.client.files.list()))
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
            
            # Verificado: el argumento correcto es 'file', no 'path'.
            # Ejecutamos en thread aparte porque es una operación I/O bloqueante.
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file=file_path,
                config={'display_name': name}
            )
            
            self._file_cache = None # Invalidar cache
            logger.info(f"Archivo subido exitosamente: {uploaded_file.uri}")

            # Polling para esperar estado ACTIVE
            logger.info(f"Esperando a que {uploaded_file.name} esté ACTIVE (Timeout 60s)...")
            for i in range(30): # Aumentado a 60 segundos (30 * 2s)
                await asyncio.sleep(2)
                try:
                    current_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    state = str(getattr(current_file, 'state', '')).upper()
                    if state == "ACTIVE":
                        logger.info(f"Archivo {uploaded_file.name} listo para usar (ACTIVE) en intento {i+1}.")
                        return current_file
                    elif state == "FAILED":
                        raise ValueError(f"Procesamiento de archivo falló: {uploaded_file.name}")
                    else:
                        if i % 5 == 0: # Log cada 10s para no saturar
                            logger.info(f"Archivo {uploaded_file.name} en estado: {state}...")
                except Exception as poll_err:
                    logger.warning(f"Error consultando estado de archivo: {poll_err}")
            
            logger.error(f"TIMEOUT CRÍTICO: El archivo {uploaded_file.name} no pasó a ACTIVE en 60s.")
            # Intentamos devolverlo de todas formas, pero logueamos error fuerte
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
            # Manejo seguro de atributos que podrían faltar si el objeto cambia
            f_name = getattr(f, 'display_name', '')
            f_name_upper = f_name.upper()
            
            # 1. CORE KERNEL
            if "CORE" in f_name_upper or "STOIC" in f_name_upper:
                relevant.append(f)
                continue
                
            # 2. TAG MATCH
            if tags_upper and any(tag in f_name_upper for tag in tags_upper):
                relevant.append(f)
                continue

            # 3. USER VAULT
            if f_name == user_vault_name:
                relevant.append(f)
        
        # Filtrar solo archivos activos
        # En el nuevo SDK, state suele ser un enum o string. Lo convertimos a str para comparar seguro.
        active_files = [f for f in relevant if str(getattr(f, 'state', '')).upper() == "ACTIVE"]
        
        if len(relevant) > len(active_files):
            logger.warning(f"Omitiendo {len(relevant) - len(active_files)} archivos en estado no-ACTIVE (processing/failed)")
            
        return active_files[:5]

    async def query_files(self, query: str, chat_id: str, tags: Optional[list[str]] = None) -> str:
        """
        Realiza búsqueda semántica inteligente (Smart RAG) en archivos relevantes.
        Refactorizado para usar system_instructions y evitar errores 400 INVALID_ARGUMENT.
        """
        relevant_files = await self.get_relevant_files(chat_id, tags)
        if not relevant_files:
            logger.info(f"No hay archivos relevantes para {chat_id} con tags {tags}")
            return ""

        logger.info(f"Smart RAG: Consultando {len(relevant_files)} archivos para {chat_id} (Tags: {tags})")
        
        try:
            model_name = settings.DEFAULT_LLM_MODEL
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")
            
            logger.info(f"Smart RAG: Usando modelo {model_name} con estrategia System Instruction.")
            
            # 1. Definir la instrucción del sistema separada del contenido del usuario
            system_instruction_text = (
                "Actúa como un extractor de sabiduría estoica y técnica.\n"
                "Basándote EXCLUSIVAMENTE en los archivos adjuntos proporcionados en el contexto, "
                "responde de forma concisa a la consulta del usuario.\n"
                "Si la información no está en los archivos, di 'Información no encontrada'.\n"
                "Estilo: Directo, sin introducciones innecesarias.\n\n"
            )

            # 2. Construir la configuración de generación
            # NOTA: En SDK 1.x antiguo, system_instruction puede fallar en config. 
            # Lo inyectamos en el prompt como fallback seguro.
            config = types.GenerateContentConfig(
                temperature=0.3
            )

            # 3. Construir el contenido del usuario (Archivos + Query)
            user_parts = []
            
            # Añadir partes de archivo
            for f in relevant_files:
                user_parts.append(types.Part.from_uri(
                    file_uri=f.uri, 
                    mime_type=f.mime_type
                ))
            
            # Inyectar instrucción + query en el texto del usuario
            full_prompt = system_instruction_text + "Consulta: " + query
            user_parts.append(types.Part.from_text(text=full_prompt))
            
            contents = [types.Content(role="user", parts=user_parts)]

            # 4. Ejecutar llamada al modelo
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config
            )

            if response and response.text:
                return response.text.strip()
            return ""

        except Exception as e:
            logger.error(f"Error en Smart RAG query_files (nuevo SDK): {e}", exc_info=True)
            # Fallback simple: intentar sin system instruction si el modelo no lo soporta (poco probable en 2.x)
            # o devolver error amigable
            return ""

    async def delete_file(self, file_name: str):
        """Elimina un archivo de la File API."""
        try:
            await asyncio.to_thread(self.client.files.delete, name=file_name)
            logger.info(f"Archivo eliminado: {file_name}")
            self._file_cache = None # Reset cache
        except Exception as e:
            logger.error(f"Error eliminando archivo con el nuevo SDK: {e}")

# Instancia singleton
file_search_tool = GoogleFileSearchTool()