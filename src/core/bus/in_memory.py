# src/core/bus/in_memory.py
import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from src.core.interfaces.bus import IEventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """
    Una implementación en memoria del IEventBus usando asyncio.Queue.

    Ideal para desarrollo local y pruebas, ya que no requiere dependencias externas.
    Cada topic es una cola de asyncio.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = (
            defaultdict(list)
        )
        self._tasks: list[asyncio.Task] = []
        logger.info("InMemoryEventBus initialized.")

    async def publish(self, topic: str, event: dict) -> None:
        """Publica un evento en la cola del topic correspondiente."""
        if topic not in self._subscribers:
            logger.warning(f"Publishing to topic '{topic}' with no subscribers.")
        await self._queues[topic].put(event)
        logger.debug(f"Event published to topic '{topic}': {event}")

    async def subscribe(
        self, topic: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Suscribe un handler a un topic y crea una tarea en segundo plano
        para consumir eventos de ese topic.
        """
        self._subscribers[topic].append(handler)
        task = asyncio.create_task(self._consumer(topic, handler))
        self._tasks.append(task)
        logger.info(f"Handler {handler.__name__} subscribed to topic '{topic}'.")

    async def _consumer(
        self, topic: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """Tarea consumidora que espera eventos en una cola y los procesa."""
        queue = self._queues[topic]
        while True:
            try:
                event = await queue.get()
                logger.debug(
                    f"Handler {handler.__name__} consumed event from '{topic}'."
                )
                await handler(event)
                queue.task_done()
            except asyncio.CancelledError:
                logger.info(f"Consumer for topic '{topic}' cancelled.")
                break
            except Exception:
                logger.exception(
                    f"Error in handler {handler.__name__} for topic '{topic}'."
                )

    async def shutdown(self) -> None:
        """Cancela todas las tareas consumidoras pendientes."""
        logger.info("Shutting down InMemoryEventBus...")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("All consumer tasks cancelled.")
