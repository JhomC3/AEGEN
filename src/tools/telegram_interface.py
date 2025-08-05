"""
Módulo para la interacción con la API de Telegram.

Este módulo proporciona una interfaz de alto nivel para realizar operaciones
comunes con la API de bots de Telegram, como descargar archivos y enviar mensajes.
Está diseñado como una herramienta reutilizable y sigue las mejores prácticas
de la arquitectura del proyecto.

LLM-hint: Siguiendo el Principio del Código de Referencia (speech_processing.py),
esta Tool se implementa como una clase. Utiliza `httpx.AsyncClient` para
comunicaciones asíncronas y obtiene la configuración (como el token del bot)
del módulo `core.config.settings`. Toda operación de I/O es `async`.
"""

import logging
from pathlib import Path
from typing import cast

import aiofiles
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class TelegramTool:
    """
    Herramienta para interactuar con la API de bots de Telegram.
    """

    def __init__(self):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if (
            not bot_token or bot_token.get_secret_value() == "YOUR_TELEGRAM_BOT_TOKEN"
        ):  # nosec B105
            raise ValueError(
                "El token del bot de Telegram no está configurado. "
                "Por favor, añádelo a tus variables de entorno (TELEGRAM_BOT_TOKEN)."
            )
        token = bot_token.get_secret_value()
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    async def get_file_path(self, file_id: str) -> str | None:
        """
        Obtiene la ruta de un archivo a partir de su file_id.
        Esta ruta es necesaria para construir la URL de descarga.
        """
        async with httpx.AsyncClient() as client:
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

    async def download_file_from_telegram(
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

        async with httpx.AsyncClient() as client:
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

    async def send_telegram_message(self, chat_id: str, text: str) -> bool:
        """
        Envía un mensaje de texto a un chat de Telegram.
        """
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {"chat_id": chat_id, "text": text}
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


# Instancia única de la herramienta para ser importada y utilizada.
telegram_tool = TelegramTool()
