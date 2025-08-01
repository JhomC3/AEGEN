"""
Test de integración para el AudioTranscriptionWorkflow.

Este test verifica el flujo completo desde la recepción de un webhook de Telegram
hasta la orquestación del workflow, asegurando que todos los componentes
internos (API, EventBus, Orchestrator, Workflow, Tools) interactúan
correctamente.
"""

import unittest
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents.orchestrator import WorkflowCoordinator
from src.core.dependencies import get_event_bus
from src.main import app

# Usamos un cliente de prueba síncrono para la API, ya que es más simple
# para este tipo de test. La app internamente sigue siendo asíncrona.
client = TestClient(app)


@pytest.fixture
def mock_event_bus_integration() -> Iterator[AsyncMock]:
    """
    Fixture que mockea el bus de eventos para los tests de integración.
    """
    mock = AsyncMock()
    app.dependency_overrides[get_event_bus] = lambda: mock
    yield mock
    app.dependency_overrides = {}


def test_telegram_webhook_to_event_bus(mock_event_bus_integration: AsyncMock):
    """
    Verifica que un webhook de audio de Telegram publica
    correctamente un evento en el bus.
    """
    # Payload de ejemplo de un mensaje de audio de Telegram
    telegram_payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 168,
            "chat": {"id": 98765, "type": "private"},
            "date": 1678886400,
            "audio": {
                "file_id": "AQADBAADG_QAAg",
                "file_unique_id": "AgADG_QAAg",
                "duration": 10,
                "mime_type": "audio/ogg",
                "file_size": 16000,
            },
        },
    }

    response = client.post("/api/v1/webhooks/telegram", json=telegram_payload)

    assert response.status_code == 202

    # Verificar que el bus de eventos fue llamado
    mock_event_bus_integration.publish.assert_called_once()

    # Extraer los argumentos con los que fue llamado
    call_args = mock_event_bus_integration.publish.call_args
    topic = call_args.args[0]
    event = call_args.args[1]

    assert topic == "workflow_events"
    assert event["task_name"] == "audio_transcription"
    assert event["chat_id"] == "98765"
    assert event["file_id"] == "AQADBAADG_QAAg"


@pytest.mark.asyncio
@patch(
    "src.agents.workflows.transcription.audio_transcriber.telegram_tool",
    new_callable=AsyncMock,
)
@patch(
    "src.agents.workflows.transcription.audio_transcriber.speech_to_text_tool",
    new_callable=AsyncMock,
)
async def test_orchestrator_runs_transcription_workflow(
    mock_speech_tool: AsyncMock, mock_telegram_tool: AsyncMock
):
    """
    Verifica que el orquestador ejecuta el workflow de transcripción
    y llama a las herramientas en la secuencia correcta.
    """
    # Configurar mocks de las herramientas
    mock_telegram_tool.download_file_from_telegram.return_value = (
        "path/to/mock/audio.ogg"
    )
    mock_speech_tool.transcribe_with_whisper.return_value = {
        "transcript": "Texto de prueba transcrito."
    }
    mock_telegram_tool.send_telegram_message.return_value = True

    # Evento que el orquestador recibiría del bus
    event_to_process = {
        "task_id": "test-123",
        "task_name": "audio_transcription",
        "chat_id": "chat-id-123",
        "file_id": "file-id-abc",
    }

    coordinator = WorkflowCoordinator()
    await coordinator.handle_workflow_event(event_to_process)

    # Verificar que las herramientas fueron llamadas en el orden correcto
    mock_telegram_tool.download_file_from_telegram.assert_called_once_with(
        file_id="file-id-abc", destination_folder=unittest.mock.ANY
    )
    mock_speech_tool.transcribe_with_whisper.assert_called_once_with(
        "path/to/mock/audio.ogg"
    )
    mock_telegram_tool.send_telegram_message.assert_called_once_with(
        "chat-id-123", "Transcripción:\n\n---\n\nTexto de prueba transcrito."
    )
