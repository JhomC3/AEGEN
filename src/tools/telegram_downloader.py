import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langchain_core.tools import tool
from telegram.files.basefile import BaseFile

logger = logging.getLogger(__name__)


@tool
@asynccontextmanager
async def download_temp_file(
    telegram_file: BaseFile, suffix: str
) -> AsyncGenerator[str, None]:
    """
    Context manager para descargar un archivo de Telegram a un directorio temporal.
    Asegura que el archivo se elimine después de su uso.

    Args:
        telegram_file: El objeto de archivo de Telegram (ej. PhotoSize, Audio, Voice).
        suffix: La extensión del archivo temporal (ej. ".jpg", ".ogg").

    Yields:
        La ruta al archivo temporal descargado.
    """
    temp_file_path = ""
    try:
        file_to_download = await telegram_file.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            logger.debug(f"Downloading file to temporary path: {temp_file_path}")
            await file_to_download.download_to_drive(temp_file_path)
            yield temp_file_path
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            logger.debug(f"Temporary file cleaned up: {temp_file_path}")
