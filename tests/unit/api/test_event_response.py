"""Regresiones del envío de respuesta y la precedencia de errores (spec 002)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.services.event_processor import _send_response


@pytest.fixture
def fake_manager(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    manager = MagicMock()
    manager.send_message = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.api.services.event_processor.telegram_interface.get_telegram_manager",
        lambda: manager,
    )
    return manager


@pytest.mark.asyncio
async def test_error_sin_respuesta_envia_error_no_fallback(
    fake_manager: MagicMock,
) -> None:
    message = await _send_response(
        "123",
        {"payload": {}, "error_message": "No hay especialistas para manejar 'audio'"},
        "task-1",
    )

    assert message == "No hay especialistas para manejar 'audio'"
    assert "respuesta vacía" not in message
    fake_manager.send_message.assert_awaited_once_with("123", message)


@pytest.mark.asyncio
async def test_error_prevalece_sobre_respuesta(fake_manager: MagicMock) -> None:
    message = await _send_response(
        "123",
        {
            "payload": {"response": "respuesta parcial"},
            "error_message": "Error inesperado al procesar solicitud.",
        },
        "task-2",
    )

    assert message == "Error inesperado al procesar solicitud."
    fake_manager.send_message.assert_awaited_once_with("123", message)


@pytest.mark.asyncio
async def test_respuesta_valida_se_envia_tal_cual(fake_manager: MagicMock) -> None:
    message = await _send_response(
        "123",
        {"payload": {"response": "  hola mundo  "}, "error_message": None},
        "task-3",
    )

    assert message == "  hola mundo  "
    fake_manager.send_message.assert_awaited_once_with("123", message)


@pytest.mark.asyncio
async def test_respuesta_vacia_y_sin_error_usa_fallback(
    fake_manager: MagicMock,
) -> None:
    message = await _send_response(
        "123",
        {"payload": {"response": "   "}, "error_message": None},
        "task-4",
    )

    assert "respuesta vacía" in message


@pytest.mark.asyncio
async def test_payload_ausente_no_lanza(fake_manager: MagicMock) -> None:
    message = await _send_response(
        "123",
        {"error_message": "Orquestador no disponible"},
        "task-5",
    )

    assert message == "Orquestador no disponible"


@pytest.mark.asyncio
async def test_fallo_de_telegram_no_relanza(
    fake_manager: MagicMock,
) -> None:
    fake_manager.send_message = AsyncMock(side_effect=RuntimeError("telegram caído"))

    message = await _send_response(
        "123",
        {"payload": {"response": "hola"}, "error_message": None},
        "task-6",
    )

    assert message == "hola"
    fake_manager.send_message.assert_awaited_once()
