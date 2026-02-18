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
        logger.info(
            "Handler %s subscribed to Redis stream '%s'.",
            handler.__name__,
            topic,
        )

    async def _ensure_consumer_group(self, topic: str, group_name: str) -> None:
        """Asegura que el grupo de consumidores exista en el stream."""
        if (topic, group_name) in self._consumer_group_created:
            return
        try:
            await self._redis.xgroup_create(topic, group_name, id="0", mkstream=True)
            logger.info(
                "Consumer group '%s' created for stream '%s'.",
                group_name,
                topic,
            )
        except RedisError as e:
            # 'BUSYGROUP' es esperado si ya existe.
            if "BUSYGROUP" not in str(e):
                logger.exception(
                    "Failed to create consumer group '%s' for stream '%s'.",
                    group_name,
                    topic,
                )
                raise
            logger.debug(
                "Consumer group '%s' already exists for stream '%s'.",
                group_name,
                topic,
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
                # '>' significa leer mensajes nuevos que no han sido
                # consumidos por nadie en el grupo
                messages = await self._redis.xreadgroup(
                    group_name, consumer_name, {topic: ">"}, count=1, block=1000
                )

                if not messages:
                    continue

                for _, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # El payload está en bytes
                            payload_str = message_data[b"payload"].decode("utf-8")
                            event = json.loads(payload_str)
                            logger.debug(
                                "Handler %s consumed event %s from '%s'.",
                                handler.__name__,
                                message_id.decode(),
                                topic,
                            )
                            await handler(event)
                            # Confirmar procesado
                            await self._redis.xack(topic, group_name, message_id)
                        except (
                            json.JSONDecodeError,
                            KeyError,
                            UnicodeDecodeError,
                        ) as e:
                            logger.error(
                                "Error processing message %s from stream '%s': %s",
                                message_id.decode(),
                                topic,
                                e,
                            )
                            # Podríamos mover el mensaje a una DLQ aquí
                        except Exception:
                            logger.exception(
                                "Unhandled error in handler %s for message %s.",
                                handler.__name__,
                                message_id.decode(),
                            )

            except asyncio.CancelledError:
                logger.info(
                    "Consumer task for handler %s on topic '%s' cancelled.",
                    handler.__name__,
                    topic,
                )
                break
            except RedisError as e:
                logger.error(
                    "Redis error in consumer for topic '%s': %s. Retrying in 5s...",
                    topic,
                    e,
                )
                await asyncio.sleep(5)
            except Exception:
                logger.exception(
                    "Unexpected error in consumer for topic '%s'. Retrying in 5s...",
                    topic,
                )
                await asyncio.sleep(5)

    async def shutdown(self) -> None:
        """Cancela todas las tareas consumidoras pendientes."""
        logger.info("Shutting down RedisEventBus...")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("All Redis consumer tasks cancelled.")
