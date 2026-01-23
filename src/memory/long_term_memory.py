# src/memory/long_term_memory.py
import json
import logging
import os
from pathlib import Path
from typing import Any

import aiofiles
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate

from src.core.config import settings
from src.core.engine import llm
from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)

# Configuración del directorio de almacenamiento local
# Configuración del directorio de almacenamiento local (Absoluta para evitar errores de CWD)
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "memory"


class LongTermMemoryManager:
    """
    Gestiona la memoria episódica de largo plazo mediante resúmenes incrementales
    y persistencia en archivos locales (optimizada para asincronía).
    """

    def __init__(self):
        # Configurar SDK nativo por si se usa File API directamente
        api_key_str = (
            settings.GOOGLE_API_KEY.get_secret_value()
            if settings.GOOGLE_API_KEY
            else ""
        )
        genai.configure(api_key=api_key_str)

        # Reutilizamos el LLM global configurado en el sistema
        self.llm = llm

        # Asegurar que el directorio de almacenamiento existe
        try:
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio de memoria verificado: {STORAGE_DIR}")
        except PermissionError:
            logger.error(f"FATAL: Sin permisos para crear '{STORAGE_DIR}'.")
        except Exception as e:
            logger.error(f"Error inesperado creando '{STORAGE_DIR}': {e}")

        logger.info("LongTermMemoryManager initialized (Hotfix v0.1.2: Async I/O)")

        self.summary_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Eres un experto en síntesis de memoria. Tu tarea es actualizar el 'Perfil Histórico' de un usuario basado en nuevos mensajes. "
                "Mantén detalles críticos como nombres, preferencias, hechos importantes y el estado de proyectos actuales. "
                "Sé conciso pero preciso. No borres información antigua a menos que haya sido corregida por el usuario.",
            ),
            (
                "user",
                "PERFIL ACTUAL:\n{current_summary}\n\nNUEVOS MENSAJES:\n{new_messages}\n\nActualiza el perfil integrando los nuevos mensajes:",
            ),
        ])

    def _get_buffer_path(self, chat_id: str) -> Path:
        return STORAGE_DIR / f"{chat_id}_buffer.json"

    def _get_local_path(self, chat_id: str) -> Path:
        """Devuelve la ruta al archivo de resumen de memoria del usuario."""
        return STORAGE_DIR / f"{chat_id}_summary.json"

    async def get_summary(self, chat_id: str) -> dict[str, Any]:
        """Recupera el resumen histórico y los mensajes en el búfer."""
        local_path = self._get_local_path(chat_id)
        buffer_path = self._get_buffer_path(chat_id)

        summary = "Sin historial previo profesional."
        raw_buffer = []

        if local_path.exists():
            try:
                async with aiofiles.open(local_path, encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                    summary = data.get("summary", summary)
            except Exception as e:
                logger.error(f"Error leyendo memoria local para {chat_id}: {e}")

        if buffer_path.exists():
            try:
                async with aiofiles.open(buffer_path, encoding="utf-8") as f:
                    content = await f.read()
                    raw_buffer = json.loads(content)
            except Exception as e:
                logger.error(f"Error leyendo búfer para {chat_id}: {e}")

        return {"summary": summary, "buffer": raw_buffer}

    async def store_raw_message(self, chat_id: str, role: str, content: str):
        """Guarda un mensaje en el búfer persistente inmediatamente."""
        buffer_path = self._get_buffer_path(chat_id)
        raw_buffer = []

        if buffer_path.exists():
            try:
                async with aiofiles.open(buffer_path, encoding="utf-8") as f:
                    content_json = await f.read()
                    raw_buffer = json.loads(content_json)
            except Exception as e:
                logger.debug(
                    f"No se pudo leer el búfer previo (normal en primera ejecución): {e}"
                )

        raw_buffer.append({"role": role, "content": content})

        # Limitar el búfer a los últimos 20 mensajes antes de forzar resumen
        if len(raw_buffer) > 20:
            raw_buffer = raw_buffer[-20:]

        try:
            async with aiofiles.open(buffer_path, mode="w", encoding="utf-8") as f:
                await f.write(json.dumps(raw_buffer, ensure_ascii=False))
            logger.info(
                f"💾 Memoria guardada en {buffer_path} ({len(raw_buffer)} msgs)"
            )
        except Exception as e:
            logger.error(f"❌ Error escribiendo memoria en {buffer_path}: {e}")

    async def update_memory(self, chat_id: str):
        """
        Analiza el búfer de mensajes, actualiza el resumen y limpia el búfer.
        """
        data = await self.get_summary(chat_id)
        current_summary = data["summary"]
        raw_buffer = data["buffer"]

        if not raw_buffer:
            return

        # Convertir búfer a texto para el resumen
        new_messages_text = "\n".join([
            f"{m['role']}: {m['content']}" for m in raw_buffer
        ])

        try:
            # Generar nuevo resumen incremental
            chain = self.summary_prompt | self.llm
            response = await chain.ainvoke({
                "current_summary": current_summary,
                "new_messages": new_messages_text,
            })

            new_summary = str(response.content).strip()

            # Persistir resumen localmente
            local_path = self._get_local_path(chat_id)
            async with aiofiles.open(local_path, mode="w", encoding="utf-8") as f:
                content = json.dumps(
                    {"summary": new_summary, "chat_id": chat_id}, ensure_ascii=False
                )
                await f.write(content)

            # Limpiar el búfer ya que ha sido consolidado en el resumen
            buffer_path = self._get_buffer_path(chat_id)
            if buffer_path.exists():
                os.remove(buffer_path)

            # --- EXTENSIÓN: Google File Search (Híbrido) ---
            try:
                # Creamos un archivo temporal con el resumen para subirlo
                user_memory_file = STORAGE_DIR / f"{chat_id}_vault.txt"
                async with aiofiles.open(
                    user_memory_file, mode="w", encoding="utf-8"
                ) as f:
                    await f.write(
                        f"Historial consolidado del usuario {chat_id}:\n\n{new_summary}"
                    )

                # Subir/Actualizar en la Google File API
                # Nota: En una implementación de producción, aquí buscaríamos si ya existe
                # para borrar el anterior o simplemente confiar en el naming.
                await file_search_tool.upload_file(
                    str(user_memory_file), display_name=f"User_Vault_{chat_id}"
                )
                logger.info(f"Bóveda en la nube actualizada para {chat_id}")
            except Exception as fe:
                logger.warning(f"No se pudo sincronizar con Google File API: {fe}")

            logger.info(f"Memoria de largo plazo consolidada para {chat_id}")

        except Exception as e:
            logger.error(
                f"Error consolidando memoria para {chat_id}: {e}", exc_info=True
            )


# Instancia singleton
long_term_memory = LongTermMemoryManager()
