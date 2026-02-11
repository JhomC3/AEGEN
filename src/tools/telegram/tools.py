from pathlib import Path

from langchain_core.tools import tool

from src.tools.telegram_interface import telegram_manager


@tool
async def download_telegram_file(file_id: str, destination_folder: str) -> str:
    """
    Tool para descargar un archivo desde Telegram a una carpeta específica.

    Args:
        file_id: El ID del archivo a descargar.
        destination_folder: La ruta de la carpeta temporal donde se guardará el archivo.

    Returns:
        La ruta local completa del archivo descargado.
    """
    destination = Path(destination_folder)
    file_path = await telegram_manager.download_file(file_id, destination)
    if not file_path:
        raise ConnectionError("No se pudo descargar el archivo desde Telegram.")
    return str(file_path)


@tool
async def reply_to_telegram_chat(chat_id: str, message: str) -> bool:
    """
    Tool para enviar un mensaje de respuesta a un chat de Telegram.
    """
    return await telegram_manager.send_message(chat_id, message)
