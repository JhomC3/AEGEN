import asyncio
import io
import logging
import mimetypes
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from src.core.config import settings

logger = logging.getLogger(__name__)

# Límites de contexto para evitar errores de "bytes too large" (400 INVALID_ARGUMENT)
MAX_USER_FILES = 5  # Perfil, Bóveda, Vault, etc.
MAX_GLOBAL_PDFS = 2  # Protocolos terapéuticos pesados
MAX_TOTAL_FILES = 8  # Límite de seguridad para la API


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

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitiza el nombre del archivo para evitar errores de codificación y caracteres no permitidos.
        Elimina acentos, convierte a ASCII y limpia caracteres especiales.
        """
        # Normalizar caracteres unicode (eliminar acentos)
        nfkd_form = unicodedata.normalize("NFKD", name)
        ascii_name = nfkd_form.encode("ASCII", "ignore").decode("ASCII")

        # Reemplazar cualquier cosa que no sea alfanumérico, punto, guion o slash por guion bajo
        sanitized = re.sub(r"[^a-zA-Z0-9./_-]", "_", ascii_name)

        # Limitar longitud para evitar errores de API (Google suele limitar a 128 o 256)
        return sanitized[:120]

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
        Sube un archivo a la Google File API eliminando versiones anteriores.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

            raw_name = f"{chat_id}/{display_name or path.name}"
            name = self._sanitize_name(raw_name)

            # Limpiar versiones previas antes de subir
            await self.delete_by_display_name(name)

            logger.info(f"Subiendo archivo a Google API como '{name}'...")

            def read_file():
                with open(path, "rb") as f:
                    return f.read()

            content_bytes = await asyncio.to_thread(read_file)
            file_io = io.BytesIO(content_bytes)

            mime_type, _ = mimetypes.guess_type(path)
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file=file_io,
                config={
                    "display_name": name,
                    "mime_type": mime_type or "application/octet-stream",
                },
            )

            self._file_cache = None  # Invalidar cache
            # 1.3: No esperamos bloqueando el flujo principal
            asyncio.create_task(self._wait_for_active(uploaded_file))
            return uploaded_file
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            raise

    async def upload_from_string(
        self, content: str, filename: str, chat_id: str, mime_type: str = "text/plain"
    ):
        """
        Sube contenido string eliminando versiones anteriores con el mismo nombre.
        """
        try:
            raw_display_name = f"{chat_id}/{filename}"
            display_name = self._sanitize_name(raw_display_name)

            # Limpiar versiones previas
            await self.delete_by_display_name(display_name)

            logger.info(f"Subiendo contenido string como '{display_name}'...")
            content_bytes = content.encode("utf-8")
            file_io = io.BytesIO(content_bytes)

            # Usamos el cliente para subir el stream
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file=file_io,
                config={"display_name": display_name, "mime_type": mime_type},
            )

            self._file_cache = None
            # 1.3: No esperamos bloqueando el flujo principal
            asyncio.create_task(self._wait_for_active(uploaded_file))
            return uploaded_file
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
                if "ACTIVE" in state:
                    logger.info(f"Archivo {uploaded_file.name} listo (ACTIVE).")
                    return current_file
                elif "FAILED" in state:
                    raise ValueError(f"Procesamiento falló: {uploaded_file.name}")

                logger.debug(
                    f"Estado de {uploaded_file.name}: {state}. Reintentando en {delay * 2}s..."
                )
            except Exception as poll_err:
                logger.warning(f"Error consultando estado: {poll_err}")

        logger.error(f"TIMEOUT: {uploaded_file.name} no pasó a ACTIVE tras reintentos.")
        return uploaded_file

    def _is_valid_rag_file(self, f: Any) -> bool:
        """Verifica si un archivo es apto para RAG (ACTIVE y no JSON)."""
        f_mime = getattr(f, "mime_type", "")
        f_state = str(getattr(f, "state", "")).upper()
        return "ACTIVE" in f_state and f_mime != "application/json"

    async def get_relevant_files(
        self,
        chat_id: str,
        tags: list[str] | None = None,
        query: str | None = None,
        intent_type: str | None = None,
    ) -> list[Any]:
        """
        Identifica qué archivos son relevantes basado en chat_id, tags e intent_type.
        Implementa deduplicación por display_name priorizando lo más reciente.
        """
        all_files = await self.list_files()

        # Paso 1: Deduplicar por display_name (solo el más reciente basado en el orden de la API)
        unique_files_map = {}
        for f in all_files:
            if not self._is_valid_rag_file(f):
                continue

            d_name = getattr(f, "display_name", "")
            # Al sobreescribir en el mapa, nos aseguramos de que si hay duplicados, no se cuenten doble en los límites.
            unique_files_map[d_name] = f

        user_files, global_pdfs, tagged_files = [], [], []
        prefix = f"{chat_id}/"
        tags_upper = [t.upper() for t in (tags or [])]
        needs_therapy = intent_type in ["vulnerability", "monitoring"] or any(
            t in ["TCC", "THERAPY", "PSYCHOLOGY"] for t in tags_upper
        )

        for disp_name, f in unique_files_map.items():
            mime = getattr(f, "mime_type", "")

            if disp_name.startswith(prefix):
                user_files.append(f)
            elif (
                disp_name.startswith("knowledge/")
                and mime == "application/pdf"
                and needs_therapy
            ):
                global_pdfs.append(f)
            elif tags_upper and any(tag in disp_name.upper() for tag in tags_upper):
                tagged_files.append(f)

        return self._compose_result(user_files, global_pdfs, tagged_files, chat_id)

    def _compose_result(
        self, user_files: list, global_pdfs: list, tagged_files: list, chat_id: str
    ) -> list[Any]:
        """Compone la lista final de archivos respetando límites y unicidad."""
        result: list[Any] = []
        seen_uris = set()

        def add(files, limit=None):
            added = 0
            for f in files:
                if (limit and added >= limit) or len(result) >= MAX_TOTAL_FILES:
                    break
                if f.uri not in seen_uris:
                    result.append(f)
                    seen_uris.add(f.uri)
                    added += 1

        add(user_files, MAX_USER_FILES)
        add(global_pdfs, MAX_GLOBAL_PDFS)
        add(tagged_files)

        logger.info(
            f"RAG Filter ({chat_id}): {len(user_files)} user, {len(global_pdfs)} therapy, "
            f"{len(tagged_files)} tagged. Selected: {len(result)}"
        )
        return result

    async def query_files(
        self,
        query: str,
        chat_id: str,
        tags: list[str] | None = None,
        intent_type: str | None = None,
    ) -> str:
        """
        Realiza búsqueda semántica inteligente (Smart RAG) en archivos relevantes.
        Usa gemini-2.5-flash-lite para optimización de costos y precisión.
        """
        relevant_files = await self.get_relevant_files(
            chat_id, tags, query=query, intent_type=intent_type
        )
        if not relevant_files:
            logger.info(f"No hay archivos relevantes para {chat_id} con tags {tags}")
            return ""

        # Log de qué archivos estamos usando
        file_names = [f.display_name for f in relevant_files]
        logger.info(
            f"Smart RAG: Consultando {len(relevant_files)} archivos para {chat_id}: {file_names}"
        )

        try:
            # Forzamos el uso de gemini-2.5-flash-lite para recuperación semántica
            model_name = "gemini-2.5-flash-lite"

            config = types.GenerateContentConfig(
                temperature=0.1,  # Menor temperatura para mayor precisión clínica
                top_p=0.95,
            )

            # Construir el prompt con contexto de archivos
            user_parts = []
            seen_uris = set()
            for f in relevant_files:
                if f.uri in seen_uris:
                    continue
                seen_uris.add(f.uri)

                # FIX: La File API no soporta application/json para RAG.
                # Si es JSON, Gemini suele fallar al leerlo vía URI si el mtype no es texto.
                # Pero no podemos mentir sobre el mtype en from_uri si la API lo valida contra el archivo.
                user_parts.append(
                    types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type)
                )

            system_instruction = (
                "Eres un experto en recuperación de memoria y análisis de perfiles de usuario.\n"
                "Tu objetivo es extraer información precisa de los archivos proporcionados.\n"
                "Prioriza archivos Markdown como 'user_profile.md' y 'knowledge_base.md'.\n"
                "Si encuentras el nombre del usuario, sus preferencias o metas, descríbelas fielmente.\n"
                "Responde siempre en el mismo idioma en el que se te hace la consulta.\n"
                "Si la información no está presente en los archivos, responde 'No encontrado'.\n"
            )

            user_parts.append(
                types.Part.from_text(text=f"{system_instruction}\nConsulta: {query}")
            )

            contents = [types.Content(role="user", parts=user_parts)]

            # type: ignore[arg-type]
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )

            if response and response.text:
                text = response.text.strip()
                if "No encontrado" in text and len(text) < 20:
                    return ""
                return text
            return ""

        except Exception as e:
            logger.error(
                f"Error en Smart RAG con gemini-2.5-flash-lite: {e}", exc_info=True
            )
            return ""

    async def search_user_history(self, chat_id: str, query: str) -> str:
        """
        5.1: Búsqueda semántica aislada en el historial profundo del usuario.
        """
        logger.info(f"Buscando en historial profundo para {chat_id}: {query}")
        # Usamos query_files sin tags globales para priorizar el historial del usuario
        return await self.query_files(query, chat_id, tags=[])

    async def delete_file(self, file_name: str):
        """Elimina un archivo por su ID interno (files/...) de la File API."""
        try:
            await asyncio.to_thread(self.client.files.delete, name=file_name)
            logger.info(f"Archivo eliminado: {file_name}")
            self._file_cache = None
        except Exception as e:
            logger.error(f"Error eliminando archivo {file_name}: {e}")

    async def delete_by_display_name(self, display_name: str):
        """Busca y elimina todos los archivos con un display_name específico."""
        try:
            all_files = await self.list_files()
            to_delete = [f.name for f in all_files if f.display_name == display_name]

            if to_delete:
                logger.info(
                    f"Limpiando {len(to_delete)} versiones antiguas de '{display_name}'..."
                )
                for file_id in to_delete:
                    await self.delete_file(file_id)
        except Exception as e:
            logger.error(f"Error limpiando por display_name '{display_name}': {e}")


# Instancia singleton
file_search_tool = GoogleFileSearchTool()
