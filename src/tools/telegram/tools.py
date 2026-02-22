from pathlib import Path

import httpx
from langchain_core.tools import tool

from src.tools.telegram_interface import telegram_manager


@tool
async def download_telegram_file(file_id: str, destination_folder: str) -> str:
    """
    Tool para descargar un archivo desde Telegram a una carpeta específica.
    """
    destination = Path(destination_folder)
    # Usar la lógica de telegram_interface.py ya que el manager no tiene
    # download_file directo
    path = await telegram_manager.get_file_path(file_id)
    if not path:
        raise ConnectionError("No se pudo obtener la ruta del archivo desde Telegram.")

    url = f"{telegram_manager.file_base_url}/{path}"
    file_name = Path(path).name
    full_path = destination / file_name

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        full_path.write_bytes(resp.content)

    return str(full_path)


@tool
async def reply_to_telegram_chat(chat_id: str, text: str) -> bool:
    """
    Tool para enviar un mensaje de respuesta a un chat de Telegram.
    Aplica protección lingüística (Escudo de Neutralidad) antes de enviar.
    """
    from src.core.lingua_guard import lingua_guard

    protected_text = await lingua_guard.protect(text)
    return await telegram_manager.send_message(chat_id, protected_text)
