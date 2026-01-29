"""
Módulo para la interacción con la API de Telegram.

Este módulo proporciona una interfaz de alto nivel para realizar operaciones
comunes con la API de bots de Telegram, como descargar archivos y enviar mensajes.
Está diseñado como una herramienta reutilizable y sigue las mejores prácticas
de la arquitectura del proyecto.
"""

import logging
import re
from pathlib import Path
from typing import cast

import aiofiles
import httpx
from langchain_core.tools import tool

from src.core.config import settings
from src.core.resilience import retry_on_failure

logger = logging.getLogger(__name__)


class TelegramToolManager:
    """
    Gestiona la lógica de negocio para interactuar con la API de Telegram.
    """

    def __init__(self):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token.get_secret_value() == "YOUR_TELEGRAM_BOT_TOKEN":  # nosec B105
            raise ValueError(
                "El token del bot de Telegram no está configurado. "
                "Por favor, añádelo a tus variables de entorno (TELEGRAM_BOT_TOKEN)."
            )
        token = bot_token.get_secret_value().strip()
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    async def get_file_path(self, file_id: str) -> str | None:
        """
        Obtiene la ruta de un archivo a partir de su file_id.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/getFile"
                response = await client.post(url, data={"file_id": file_id})
                response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    return cast(str, data["result"]["file_path"])
                logger.error(
                    f"La API de Telegram devolvió un error: {data.get('description')}"
                )
                return None
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Error de estado HTTP al obtener la ruta del archivo: {e}",
                    exc_info=True,
                )
                return None
            except Exception as e:
                logger.error(
                    f"Error inesperado al obtener la ruta del archivo: {e}",
                    exc_info=True,
                )
                return None

    async def download_file(
        self, file_id: str, destination_folder: Path
    ) -> Path | None:
        """
        Descarga un archivo de Telegram y lo guarda en una carpeta de destino.
        """
        file_path_suffix = await self.get_file_path(file_id)
        if not file_path_suffix:
            return None

        download_url = f"{self.file_base_url}/{file_path_suffix}"
        local_filename = Path(file_path_suffix).name
        destination_path = destination_folder / local_filename

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info(f"Descargando archivo de Telegram: {download_url}")
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    destination_folder.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(destination_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                logger.info(f"Archivo guardado exitosamente en: {destination_path}")
                return destination_path
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Error de estado HTTP durante la descarga: {e}", exc_info=True
                )
                return None
            except Exception as e:
                logger.error(
                    f"Error inesperado durante la descarga: {e}", exc_info=True
                )
                return None

    def _clean_markdown(self, text: str) -> str:
        """
        Limpia residuos de markdown (**, __, `) para envío seguro en texto plano.
        """
        # Eliminar negritas (**texto** -> texto)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        # Eliminar cursivas (__texto__ -> texto)
        text = re.sub(r"__(.*?)__", r"\1", text)
        # Eliminar código inline (`texto` -> texto)
        text = re.sub(r"`(.*?)`", r"\1", text)
        # Eliminar bloques de código (```texto``` -> texto)
        text = re.sub(r"```(.*?)```", r"\1", text, flags=re.DOTALL)
        return text

    @retry_on_failure(retries=3, delay=2.0, backoff=2.0)
    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Envía un mensaje de texto a un chat de Telegram.
        Limpia markdown para evitar errores 400 y envía como texto plano.
        """
        clean_text = self._clean_markdown(text)

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": clean_text,
                    # Sin parse_mode: enviamos texto plano seguro
                }
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    logger.info(f"Mensaje enviado exitosamente al chat_id: {chat_id}")
                    return True
                logger.error(
                    f"La API de Telegram devolvió un error al enviar el mensaje: {data.get('description')}"
                )
                return False
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Error de estado HTTP al enviar el mensaje: {e}", exc_info=True
                )
                return False
            except Exception as e:
                logger.error(
                    f"Error inesperado al enviar el mensaje: {e}", exc_info=True
                )
                return False

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        """
        Envía una acción de chat (ej: typing, upload_photo, record_voice) a Telegram.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.base_url}/sendChatAction"
                payload = {"chat_id": chat_id, "action": action}
                response = await client.post(url, json=payload)
                return response.status_code == 200
            except Exception as e:
                logger.warning(
                    f"No se pudo enviar ChatAction '{action}' a Telegram: {e}"
                )
                return False


# Instancia única del gestor para ser utilizada por las herramientas.
telegram_manager = TelegramToolManager()


@tool
async def download_telegram_audio(file_id: str, destination_folder: str) -> str:
    """
    Tool para descargar un archivo de audio desde Telegram a una carpeta específica.

    Args:
        file_id: El ID del archivo a descargar.
        destination_folder: La ruta de la carpeta temporal donde se guardará el archivo.

    Returns:
        La ruta local completa del archivo descargado.
    """
    destination = Path(destination_folder)
    file_path = await telegram_manager.download_file(file_id, destination)
    if not file_path:
        raise ConnectionError(
            "No se pudo descargar el archivo de audio desde Telegram."
        )
    return str(file_path)


@tool
async def reply_to_telegram_chat(chat_id: str, message: str) -> bool:
    """
    Tool para enviar un mensaje de respuesta a un chat de Telegram.
    """
    return await telegram_manager.send_message(chat_id, message)
