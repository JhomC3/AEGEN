# tests/integration/test_telegram_webhook.py
import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest
import respx
from httpx import AsyncClient

from src.core.schemas import CanonicalEventV1, GraphStateV1


@pytest.mark.asyncio
@respx.mock
async def test_telegram_webhook_success_flow(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """
    Test de integración para el flujo exitoso del webhook de Telegram.
    Simula la recepción de un audio, su procesamiento y la respuesta.
    """
    # 1. Setup de Mocks
    # Mockear el agente de transcripción para aislar el test al adaptador
    mock_agent_run = AsyncMock(
        return_value=GraphStateV1(
            event=CanonicalEventV1(
                event_id=uuid4(),
                source="telegram",
                chat_id=12345,
                user_id=12345,
                file_id="file-id",
                content=None,
            ),
            payload={"transcription": "Este es un texto de prueba."},
            error_message=None,
        )
    )
    monkeypatch.setattr(
        "src.agents.specialists.transcription_agent.transcription_agent.run",
        mock_agent_run,
    )

    # Mockear la herramienta de descarga de Telegram
    mock_download_tool = MagicMock()
    mock_download_tool.ainvoke = AsyncMock(return_value="/tmp/fake_audio.ogg")
    monkeypatch.setattr(
        "src.tools.telegram_interface.download_telegram_audio",
        mock_download_tool,
    )

    # Mockear la herramienta de respuesta de Telegram
    mock_reply_tool = MagicMock()
    mock_reply_tool.ainvoke = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.tools.telegram_interface.reply_to_telegram_chat",
        mock_reply_tool,
    )

    # 2. Preparar la Petición
    test_chat_id = 12345
    test_file_id = "AwACAgADbRIADe4uGg"
    test_file_unique_id = "unique-id-123"
    test_user_id = 54321

    # Payload válido que simula un TelegramUpdate real
    webhook_payload = {
        "update_id": 987654321,
        "message": {
            "message_id": 123,
            "date": 1678886400,
            "chat": {"id": test_chat_id, "type": "private", "username": "testuser"},
            "from": {
                "id": test_user_id,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en",
            },
            "voice": {
                "file_id": test_file_id,
                "file_unique_id": test_file_unique_id,
                "duration": 5,
                "mime_type": "audio/ogg",
            },
        },
    }

    # 3. Ejecutar la Petición
    response = await async_client.post(
        "/api/v1/webhooks/telegram", json=webhook_payload
    )

    # 4. Verificar la Respuesta Inmediata
    assert response.status_code == 202
    response_data = response.json()
    assert response_data["message"] == "Telegram event accepted for processing."
    assert "task_id" in response_data

    # 5. Verificar el Proceso en Segundo Plano
    # Esperar un breve momento para que la tarea en segundo plano se ejecute
    await asyncio.sleep(0.1)

    # Verificar que la herramienta de descarga fue llamada correctamente
    mock_download_tool.ainvoke.assert_awaited_once_with(
        {
            "file_id": test_file_id,
            "destination_folder": ANY,
        }
    )

    # Verificar que el agente de transcripción fue llamado con el estado correcto
    mock_agent_run.assert_awaited_once()
    call_args = mock_agent_run.call_args[0][0]
    assert isinstance(call_args, GraphStateV1)
    assert call_args.payload["audio_file_path"] == "/tmp/fake_audio.ogg"

    # Verificar que la herramienta de respuesta fue llamada con el texto correcto
    expected_message = "Transcripción:\n\n---\n\nEste es un texto de prueba."
    mock_reply_tool.ainvoke.assert_awaited_once_with(
        {
            "chat_id": str(test_chat_id),
            "message": expected_message,
        }
    )
