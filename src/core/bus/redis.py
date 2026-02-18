# src/core/bus/redis.py
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from src.core.interfaces.bus import IEventBus

logger = logging.getLogger(__name__)


class RedisEventBus(IEventBus):
    """
    Una implementación del IEventBus utilizando Redis Streams.

    Esta implementación permite una comunicación de eventos robusta y persistente,
    adecuada para un entorno de producción distribuido.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._tasks: list[asyncio.Task] = []
        self._consumer_group_created: set[tuple[str, str]] = set()
        logger.info("RedisEventBus initialized.")

    async def publish(self, topic: str, event: dict) -> None:
        """Publica un evento en un Redis Stream."""
        try:
            # Serializar el evento a JSON para almacenarlo en un único campo
            payload = json.dumps(event)
            await self._redis.xadd(topic, {"payload": payload})
            logger.debug(f"Event published to Redis stream '{topic}': {event}")
        except RedisError as e:
            logger.exception(
                f"Failed to publish event to Redis stream '{topic}'. Error: {e}"
            )
            # Re-lanzar la excepción para que el llamador pueda manejarla
            raise

    async def subscribe(
        self, topic: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Suscribe un handler a un topic (stream) y crea un consumidor en segundo plano.
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

        # Crear una tarea consumidora para este topic si aún no existe
        # Para simplificar, creamos una tarea por handler suscrito
        task = asyncio.create_task(self._consumer(topic, handler))
        self._tasks.append(task)
        logger.info(f"Handler {handler.__name__} subscribed to Redis stream '{topic}'.")

    async def _ensure_consumer_group(self, topic: str, group_name: str) -> None:
        """Asegura que el grupo de consumidores exista en el stream."""
        if (topic, group_name) in self._consumer_group_created:
            return
        try:
            await self._redis.xgroup_create(topic, group_name, id="0", mkstream=True)
            logger.info(f"Consumer group '{group_name}' created for stream '{topic}'.")
        except RedisError as e:
            # 'BUSYGROUP Consumer Group name already exists' es esperado si ya existe.
            if "BUSYGROUP" not in str(e):
                logger.exception(
                    f"Failed to create consumer group '{group_name}' for stream '{topic}'."
                )
                raise
            logger.debug(
                f"Consumer group '{group_name}' already exists for stream '{topic}'."
            )
        self._consumer_group_created.add((topic, group_name))

    async def _consumer(
        self, topic: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Tarea consumidora que lee eventos de un stream de Redis usando un grupo.
        """
        # Usar el nombre del handler para crear un consumidor único dentro del grupo
        group_name = f"{topic}-group"
        consumer_name = f"{handler.__name__}-{id(self)}"
        await self._ensure_consumer_group(topic, group_name)

        while True:
            try:
                # Leer nuevos mensajes del stream para este grupo
                # '>' significa leer mensajes nuevos que no han sido consumidos por nadie en el grupo
                messages = await self._redis.xreadgroup(
                    group_name, consumer_name, {topic: ">"}, count=1, block=1000
                )

                if not messages:
                    continue

                for _, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # El payload está en bytes, decodificar y deserializar
                            payload_str = message_data[b"payload"].decode("utf-8")
                            event = json.loads(payload_str)
                            logger.debug(
                                f"Handler {handler.__name__} consumed event "
                                f"{message_id.decode()} from '{topic}'."
                            )
                            await handler(event)
                            # Confirmar que el mensaje ha sido procesado
                            await self._redis.xack(topic, group_name, message_id)
                        except (
                            json.JSONDecodeError,
                            KeyError,
                            UnicodeDecodeError,
                        ) as e:
                            logger.error(
                                f"Error processing message {message_id.decode()} "
                                f"from stream '{topic}': {e}"
                            )
                            # Podríamos mover el mensaje a una DLQ aquí
                        except Exception:
                            logger.exception(
                                f"Unhandled error in handler {handler.__name__} "
                                f"for message {message_id.decode()}."
                            )

            except asyncio.CancelledError:
                logger.info(
                    f"Consumer task for handler {handler.__name__} "
                    f"on topic '{topic}' cancelled."
                )
                break
            except RedisError as e:
                logger.error(
                    f"Redis error in consumer for topic '{topic}': {e}. "
                    "Retrying in 5s..."
                )
                await asyncio.sleep(5)
            except Exception:
                logger.exception(
                    f"Unexpected error in consumer for topic '{topic}'. "
                    "Retrying in 5s..."
                )
                await asyncio.sleep(5)

    async def shutdown(self) -> None:
        """Cancela todas las tareas consumidoras pendientes."""
        logger.info("Shutting down RedisEventBus...")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("All Redis consumer tasks cancelled.")
