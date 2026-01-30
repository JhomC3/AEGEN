import asyncio
import io
import logging
import time
from pathlib import Path
from typing import Any

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
        api_key = (
            settings.GOOGLE_API_KEY.get_secret_value()
            if settings.GOOGLE_API_KEY
            else ""
        )
        self.client = genai.Client(api_key=api_key)
        self._file_cache = None
        self._last_cache_update = 0
        self.CACHE_TTL = 300  # 5 minutos
        logger.info(
            f"GoogleFileSearchTool inicializada. SDK google.genai version: {getattr(genai, '__version__', 'unknown')}"
        )

    async def list_files(self):
        """
        Lista los archivos disponibles en la File API con cache.
        """
        current_time = time.time()
        if self._file_cache and (
            current_time - self._last_cache_update < self.CACHE_TTL
        ):
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

    async def upload_file(
        self, file_path: str, chat_id: str, display_name: str | None = None
    ):
        """
        Sube un archivo a la Google File API con aislamiento por chat_id.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

            # 1.4: Añadir prefijo {chat_id}/ para aislamiento
            name = f"{chat_id}/{display_name or path.name}"
            logger.info(f"Subiendo archivo {path.name} como '{name}'...")

            uploaded_file = await asyncio.to_thread(
                self.client.files.upload, file=file_path, config={"display_name": name}
            )

            self._file_cache = None  # Invalidar cache
            return await self._wait_for_active(uploaded_file)
        except Exception as e:
            logger.error(f"Error subiendo archivo {file_path}: {e}")
            raise

    async def upload_from_string(
        self, content: str, filename: str, chat_id: str, mime_type: str = "text/plain"
    ):
        """
        1.2: Sube contenido directamente desde un string (Diskless).
        Asegura aislamiento por chat_id.
        """
        try:
            # 1.4: Prefijo chat_id
            display_name = f"{chat_id}/{filename}"
            logger.info(f"Subiendo contenido string como '{display_name}'...")

            # Convertir string a stream de bytes
            content_bytes = content.encode("utf-8")
            file_io = io.BytesIO(content_bytes)

            # Usamos el cliente para subir el stream
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file=file_io,
                config={"display_name": display_name, "mime_type": mime_type},
            )

            self._file_cache = None
            return await self._wait_for_active(uploaded_file)
        except Exception as e:
            logger.error(f"Error en upload_from_string para {filename}: {e}")
            raise

    async def download_to_string(self, filename: str, chat_id: str) -> str:
        """
        1.3: Intenta obtener el contenido de un archivo.
        ADVERTENCIA: La Google File API no permite descarga directa de contenido.
        Este método es un placeholder para consistencia arquitectónica, pero
        la fuente de verdad para el sistema debe ser Redis.
        """
        display_name = f"{chat_id}/{filename}"
        logger.warning(
            f"download_to_string llamado para {display_name}. "
            "La File API es de solo escritura (para RAG). Recuperando de caché/Redis si es posible."
        )
        # Por ahora devolvemos vacío ya que la API no lo soporta.
        # En el futuro, si usamos GCS, aquí iría la lógica de descarga.
        return ""

    async def _wait_for_active(self, uploaded_file: Any):
        """Helper para esperar a que un archivo esté ACTIVE con exponential backoff."""
        logger.info(f"Esperando a que {uploaded_file.name} esté ACTIVE...")

        # B.6: Exponential Backoff (2s, 4s, 8s, 16s, 32s, 60s)
        delays = [2, 4, 8, 16, 32, 60]

        for delay in delays:
            await asyncio.sleep(delay)
            try:
                current_file = await asyncio.to_thread(
                    self.client.files.get, name=uploaded_file.name
                )
                state = str(getattr(current_file, "state", "")).upper()
                if state == "ACTIVE":
                    logger.info(f"Archivo {uploaded_file.name} listo (ACTIVE).")
                    return current_file
                elif state == "FAILED":
                    raise ValueError(f"Procesamiento falló: {uploaded_file.name}")

                logger.debug(
                    f"Estado de {uploaded_file.name}: {state}. Reintentando en {delay * 2}s..."
                )
            except Exception as poll_err:
                logger.warning(f"Error consultando estado: {poll_err}")

        logger.error(f"TIMEOUT: {uploaded_file.name} no pasó a ACTIVE tras reintentos.")
        return uploaded_file

    async def get_relevant_files(
        self, chat_id: str, tags: list[str] | None = None
    ) -> list[Any]:
        """
        Identifica qué archivos son relevantes basado en chat_id (prefijo) y tags.
        """
        all_files = await self.list_files()
        relevant = []

        # Prefijo obligatorio para aislamiento
        prefix = f"{chat_id}/"
        tags_upper = [t.upper() for t in (tags or [])]

        for f in all_files:
            f_display_name = getattr(f, "display_name", "")

            # 1. Aislamiento por chat_id (Obligatorio para archivos de usuario)
            if f_display_name.startswith(prefix):
                relevant.append(f)
                continue

            # 2. CORE KERNEL & KNOWLEDGE (Global para todos los usuarios)
            f_name_upper = f_display_name.upper()
            is_global = any(
                term in f_name_upper
                for term in ["CORE", "STOIC", "KNOWLEDGE", "GLOBAL"]
            ) or f_display_name.startswith("knowledge/")

            if is_global:
                relevant.append(f)
                continue

            # 3. TAG MATCH (Si no tiene prefijo pero coincide con tag global)
            if tags_upper and any(tag in f_name_upper for tag in tags_upper):
                relevant.append(f)

        # Filtrar solo activos y limitar
        active_files = [
            f for f in relevant if str(getattr(f, "state", "")).upper() == "ACTIVE"
        ]
        return active_files[:10]  # Aumentado a 10 para mayor contexto

    async def query_files(
        self, query: str, chat_id: str, tags: list[str] | None = None
    ) -> str:
        """
        Realiza búsqueda semántica inteligente (Smart RAG) en archivos relevantes.
        """
        relevant_files = await self.get_relevant_files(chat_id, tags)
        if not relevant_files:
            logger.info(f"No hay archivos relevantes para {chat_id} con tags {tags}")
            return ""

        # Log de qué archivos estamos usando
        file_names = [f.display_name for f in relevant_files]
        logger.info(
            f"Smart RAG: Consultando {len(relevant_files)} archivos para {chat_id}: {file_names}"
        )

        try:
            model_name = settings.DEFAULT_LLM_MODEL
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")

            config = types.GenerateContentConfig(temperature=0.3)

            # Construir el prompt con contexto de archivos
            user_parts = []
            for f in relevant_files:
                user_parts.append(
                    types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type)
                )

            system_instruction = (
                "Eres un asistente que recupera información histórica y técnica con precisión clínica.\n"
                "Usa los archivos proporcionados para responder a la consulta.\n"
                "Si la información no está, di 'No encontrado'.\n"
            )

            user_parts.append(
                types.Part.from_text(text=f"{system_instruction}\nConsulta: {query}")
            )

            contents = [types.Content(role="user", parts=user_parts)]

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )

            if response and response.text:
                return response.text.strip()
            return ""

        except Exception as e:
            logger.error(f"Error en Smart RAG: {e}", exc_info=True)
            return ""

    async def search_user_history(self, chat_id: str, query: str) -> str:
        """
        5.1: Búsqueda semántica aislada en el historial profundo del usuario.
        """
        logger.info(f"Buscando en historial profundo para {chat_id}: {query}")
        # Usamos query_files sin tags globales para priorizar el historial del usuario
        return await self.query_files(query, chat_id, tags=[])

    async def delete_file(self, file_name: str):
        """Elimina un archivo de la File API."""
        try:
            await asyncio.to_thread(self.client.files.delete, name=file_name)
            logger.info(f"Archivo eliminado: {file_name}")
            self._file_cache = None  # Reset cache
        except Exception as e:
            logger.error(f"Error eliminando archivo con el nuevo SDK: {e}")


# Instancia singleton
file_search_tool = GoogleFileSearchTool()
