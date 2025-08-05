# tests/unit/core/bus/test_in_memory.py
import asyncio
from unittest.mock import AsyncMock

import pytest

from src.core.bus.in_memory import InMemoryEventBus


@pytest.fixture
async def event_bus():
    """Fixture para crear una instancia del event bus y limpiarla después."""
    bus = InMemoryEventBus()
    yield bus
    # El shutdown es crucial para cancelar las tareas consumidoras
    await bus.shutdown()


@pytest.mark.asyncio
async def test_publish_to_topic_with_subscriber(event_bus: InMemoryEventBus):
    """
    Verifica que un handler suscrito recibe el evento publicado.
    """
    # Mock del handler para espiar sus llamadas
    mock_handler = AsyncMock()
    topic = "test_topic"
    event = {"key": "value"}

    await event_bus.subscribe(topic, mock_handler)

    # Dar un pequeño respiro para que la tarea consumidora se inicie
    await asyncio.sleep(0.01)

    await event_bus.publish(topic, event)

    # Esperar a que el evento sea procesado
    await asyncio.sleep(0.01)

    mock_handler.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_handler_not_called_for_different_topic(event_bus: InMemoryEventBus):
    """
    Verifica que un handler no recibe eventos de topics a los que no está suscrito.
    """
    mock_handler = AsyncMock()
    await event_bus.subscribe("topic_a", mock_handler)
    await asyncio.sleep(0.01)

    await event_bus.publish("topic_b", {"data": "some_data"})
    await asyncio.sleep(0.01)

    mock_handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_multiple_handlers_for_same_topic(event_bus: InMemoryEventBus):
    """
    Verifica que múltiples handlers para el mismo topic reciben el evento.
    """
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    topic = "shared_topic"
    event = {"id": 123}

    await event_bus.subscribe(topic, handler1)
    await event_bus.subscribe(topic, handler2)
    await asyncio.sleep(0.01)

    await event_bus.publish(topic, event)
    await asyncio.sleep(0.01)

    handler1.assert_awaited_once_with(event)
    handler2.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_logs_warning(
    event_bus: InMemoryEventBus, caplog
):
    """
    Verifica que se emite un warning al publicar en un topic sin suscriptores.
    """
    await event_bus.publish("unsubscribed_topic", {"message": "hello?"})
    assert "Publishing to topic 'unsubscribed_topic' with no subscribers" in caplog.text


@pytest.mark.asyncio
async def test_shutdown_cancels_consumer_tasks(event_bus: InMemoryEventBus):
    """
    Verifica que el método shutdown cancela correctamente las tareas consumidoras.
    """
    handler = AsyncMock()
    await event_bus.subscribe("persistent_topic", handler)

    # Verificar que la tarea consumidora está corriendo
    assert len(event_bus._consumer_tasks) == 1
    task = list(event_bus._consumer_tasks.values())[0]
    assert not task.done()

    # Llamar a shutdown
    await event_bus.shutdown()

    # Verificar que la tarea fue cancelada
    assert task.done()
    assert task.cancelled()
