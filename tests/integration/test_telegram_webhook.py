# tests/integration/test_telegram_webhook.py
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from httpx import AsyncClient

from src.core.schemas import CanonicalEventV1


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
    # Mockear el orquestador principal para aislar el test al adaptador
    mock_orchestrator_run = AsyncMock(
        return_value={
            "event": CanonicalEventV1(
                source="telegram",
                event_type="audio",
                chat_id=12345,
                user_id=12345,
                file_id="file-id",
                content=None,
                timestamp="2023-01-01T00:00:00",
                first_name="TestUser",
                language_code="es",
            ),
            "payload": {"response": "Este es un texto de prueba."},
            "error_message": None,
        }
    )
    monkeypatch.setattr(
        "src.api.services.event_processor.master_orchestrator.run",
        mock_orchestrator_run,
    )

    # Mockear la herramienta de descarga de Telegram
    mock_download_tool = MagicMock()
    mock_download_tool.ainvoke = AsyncMock(return_value="/tmp/fake_audio.ogg")
    monkeypatch.setattr(
        "src.tools.telegram_interface.download_telegram_file",
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

    webhook_payload = {
        "update_id": 987654321,
        "message": {
            "message_id": 123,
            "date": 1678886400,
            "chat": {"id": test_chat_id, "type": "private"},
            "voice": {
                "file_id": test_file_id,
                "file_unique_id": "unique-id-123",
                "duration": 5,
                "mime_type": "audio/ogg",
            },
        },
    }

    # Mockear el buffer de ingestión
    mock_ingestion_buffer = AsyncMock()
    mock_ingestion_buffer.push_event = AsyncMock(return_value=1)
    mock_ingestion_buffer.get_current_sequence = AsyncMock(return_value=1)
    mock_ingestion_buffer.flush_all = AsyncMock(
        return_value=[
            {
                "event_type": "audio",
                "content": None,
                "file_id": test_file_id,
                "language_code": "es",
            }
        ]
    )
    monkeypatch.setattr(
        "src.api.adapters.telegram_adapter.ingestion_buffer", mock_ingestion_buffer
    )
    monkeypatch.setattr(
        "src.api.services.debounce_manager.ingestion_buffer", mock_ingestion_buffer
    )

    # 3. Ejecutar la Petición
    response = await async_client.post(
        "/api/v1/webhooks/telegram", json=webhook_payload
    )

    # 4. Verificar la Respuesta Inmediata
    assert response.status_code == 202
    response_data = response.json()
    assert response_data["message"] == "Telegram event accepted and buffered."
    assert "task_id" in response_data

    # 5. Verificar el Proceso en Segundo Plano (Consolidación)
    # Aumentamos el sleep para dar tiempo al debounce (aunque en test debería ser rápido)
    await asyncio.sleep(3.5)

    mock_download_tool.ainvoke.assert_awaited_once()

    # Verificar que el orquestador fue invocado con el estado correcto
    mock_orchestrator_run.assert_awaited_once()
    call_args = mock_orchestrator_run.call_args[0][0]
    assert isinstance(call_args, dict)  # El estado es un dict
    assert call_args.get("payload", {}).get("audio_file_path") == "/tmp/fake_audio.ogg"

    # Verificar que la herramienta de respuesta fue llamada con el texto correcto
    expected_message = "Este es un texto de prueba."
    mock_reply_tool.ainvoke.assert_awaited_once_with({
        "chat_id": str(test_chat_id),
        "message": expected_message,
    })
