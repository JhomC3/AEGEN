"""
Tests unitarios para la TelegramTool.

Estos tests verifican que la herramienta de interfaz de Telegram construye
correctamente las peticiones a la API de Telegram y maneja las respuestas
esperadas (tanto exitosas como de error) sin realizar llamadas de red reales.
"""

import json
from pathlib import Path

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from src.tools.telegram_interface import TelegramToolManager

# Constantes para los tests
BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_BASE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}"


@pytest.fixture
def telegram_tool(monkeypatch) -> TelegramToolManager:
    """
    Fixture que proporciona una instancia de la TelegramToolManager, mockeando
    el token de Telegram en la configuración para el entorno de prueba.
    """
    # Mockea la configuración para que la herramienta use el token de prueba
    monkeypatch.setattr(
        "src.core.config.settings.TELEGRAM_BOT_TOKEN", SecretStr(BOT_TOKEN)
    )
    return TelegramToolManager()


@respx.mock
@pytest.mark.asyncio
async def test_get_file_path_success(telegram_tool: TelegramToolManager):
    """
    Verifica que get_file_path maneja una respuesta exitosa de la API.
    """
    file_id = "test_file_id"
    expected_file_path = "photos/file_0.jpg"

    # Mock de la ruta de la API
    get_file_route = respx.post(f"{BASE_URL}/getFile").mock(
        return_value=Response(
            200, json={"ok": True, "result": {"file_path": expected_file_path}}
        )
    )

    file_path = await telegram_tool.get_file_path(file_id)

    assert file_path == expected_file_path
    assert get_file_route.called


@respx.mock
@pytest.mark.asyncio
async def test_get_file_path_api_error(telegram_tool: TelegramToolManager):
    """
    Verifica que get_file_path maneja una respuesta de error de la API.
    """
    file_id = "test_file_id"

    get_file_route = respx.post(f"{BASE_URL}/getFile").mock(
        return_value=Response(200, json={"ok": False, "description": "File not found"})
    )

    file_path = await telegram_tool.get_file_path(file_id)

    assert file_path is None
    assert get_file_route.called


@respx.mock
@pytest.mark.asyncio
async def test_download_file_success(telegram_tool: TelegramToolManager, tmp_path: Path):
    """
    Verifica la descarga exitosa de un archivo.
    """
    file_id = "test_file_id"
    file_path_suffix = "documents/test_document.pdf"
    file_content = b"Este es un documento de prueba."

    # Mock para get_file_path
    respx.post(f"{BASE_URL}/getFile").mock(
        return_value=Response(
            200, json={"ok": True, "result": {"file_path": file_path_suffix}}
        )
    )

    # Mock para la descarga del archivo
    download_route = respx.get(f"{FILE_BASE_URL}/{file_path_suffix}").mock(
        return_value=Response(200, content=file_content)
    )

    destination_path = await telegram_tool.download_file(
        file_id, tmp_path
    )

    assert destination_path is not None
    assert destination_path.name == "test_document.pdf"
    assert destination_path.read_bytes() == file_content
    assert download_route.called


@respx.mock
@pytest.mark.asyncio
async def test_send_message_success(telegram_tool: TelegramToolManager):
    """
    Verifica el envío exitoso de un mensaje.
    """
    chat_id = "12345"
    text = "Hola Mundo"

    send_message_route = respx.post(f"{BASE_URL}/sendMessage").mock(
        return_value=Response(200, json={"ok": True, "result": {"message_id": 999}})
    )

    success = await telegram_tool.send_message(chat_id, text)

    assert success is True
    assert send_message_route.called
    request = send_message_route.calls.last.request
    # Cargar el contenido del body para una comparación robusta de JSON
    sent_data = json.loads(request.content)
    assert sent_data == {"chat_id": chat_id, "text": text}


@respx.mock
@pytest.mark.asyncio
async def test_send_message_failure(telegram_tool: TelegramToolManager):
    """
    Verifica el manejo de un fallo al enviar un mensaje.
    """
    chat_id = "12345"
    text = "Hola Mundo"

    send_message_route = respx.post(f"{BASE_URL}/sendMessage").mock(
        return_value=Response(400, json={"ok": False, "description": "Chat not found"})
    )

    success = await telegram_tool.send_message(chat_id, text)

    assert success is False
    assert send_message_route.called
