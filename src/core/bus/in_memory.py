# src/core/bus/in_memory.py
import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from src.core.interfaces.bus import IEventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """
    Una implementación en memoria del IEventBus.

    Implementa un patrón fan-out: un único consumidor por topic que distribuye
    el evento a múltiples handlers suscritos.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = (
            defaultdict(list)
        )
        self._consumer_tasks: dict[str, asyncio.Task] = {}
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
        Suscribe un handler a un topic.

        Si es la primera suscripción para este topic, crea una única
        tarea consumidora en segundo plano.
        """
        # Añadir el handler a la lista de suscriptores para este topic
        self._subscribers[topic].append(handler)

        # Si no hay una tarea consumidora para este topic, crearla.
        if topic not in self._consumer_tasks:
            task = asyncio.create_task(self._consumer(topic))
            self._consumer_tasks[topic] = task
            logger.info(f"Consumer task created for topic '{topic}'.")

        logger.info(f"Handler {handler.__name__} subscribed to topic '{topic}'.")

    async def _consumer(self, topic: str) -> None:
        """
        Tarea consumidora que espera eventos en una cola y los distribuye
        a todos los handlers suscritos.
        """
        queue = self._queues[topic]
        while True:
            try:
                event = await queue.get()
                logger.debug(
                    f"Consumed event from '{topic}', distributing to handlers."
                )

                # Obtener todos los handlers para este topic
                handlers = self._subscribers.get(topic, [])
                if handlers:
                    # Ejecutar todos los handlers concurrentemente
                    await asyncio.gather(*(handler(event) for handler in handlers))

                queue.task_done()
            except asyncio.CancelledError:
                logger.info(f"Consumer for topic '{topic}' cancelled.")
                break
            except Exception:
                logger.exception(f"Error in consumer for topic '{topic}'.")

    async def shutdown(self) -> None:
        """Cancela todas las tareas consumidoras pendientes."""
        logger.info("Shutting down InMemoryEventBus...")
        tasks_to_cancel = list(self._consumer_tasks.values())
        for task in tasks_to_cancel:
            task.cancel()
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        logger.info("All consumer tasks cancelled.")
