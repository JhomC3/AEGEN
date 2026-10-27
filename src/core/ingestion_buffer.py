# src/core/ingestion_buffer.py
import json
import logging
from typing import Any

from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class IngestionBuffer:
    """
    Buffer atómico para acumulación de fragmentos de mensajes (Debounce).
    Permite capturar ráfagas de mensajes y procesarlos como uno solo.
    """

    BUFFER_TTL_SECONDS = 60
    # Ventana de recuperación tras un apagado ordenado. Sin esto, un reinicio
    # más largo que el TTL de la ráfaga perdería los mensajes pendientes.
    SHUTDOWN_RECOVERY_TTL_SECONDS = 3600

    def __init__(self) -> None:
        self.MSG_BUFFER_PREFIX = "ingest:buffer:"
        self.SEQ_COUNTER_PREFIX = "ingest:seq:"

    def _get_redis(self) -> aioredis.Redis:
        from src.core.dependencies import redis_connection

        if redis_connection is None:
            raise RuntimeError("Redis connection not available for IngestionBuffer")
        return redis_connection

    async def push_event(self, chat_id: str, event_data: dict[str, Any]) -> int:
        """
        Guarda un fragmento de evento y aumenta el contador de secuencia.
        Retorna el nuevo número de secuencia.
        """
        redis = self._get_redis()
        buffer_key = f"{self.MSG_BUFFER_PREFIX}{chat_id}"
        seq_key = f"{self.SEQ_COUNTER_PREFIX}{chat_id}"

        # 1. Guardar el fragmento (lista)
        payload = json.dumps(event_data, ensure_ascii=False)
        await redis.rpush(buffer_key, payload)

        # 2. Incrementar secuencia (atómico)
        current_seq = await redis.incr(seq_key)

        # 3. Establecer TTL corto (evitar fugas si algo falla)
        await redis.expire(buffer_key, self.BUFFER_TTL_SECONDS)
        await redis.expire(seq_key, self.BUFFER_TTL_SECONDS)

        logger.debug(
            f"Event pushed to ingestion buffer for {chat_id}. Seq: {current_seq}"
        )
        return current_seq

    async def refresh_ttl(self, chat_id: str) -> None:
        """Renueva el TTL mientras hay una ráfaga esperando el cerrojo.

        Sin esto, una espera superior al TTL haría desaparecer los mensajes
        pendientes aunque la tarea siguiera viva.
        """
        redis = self._get_redis()
        buffer_key = f"{self.MSG_BUFFER_PREFIX}{chat_id}"
        seq_key = f"{self.SEQ_COUNTER_PREFIX}{chat_id}"
        await redis.expire(buffer_key, self.BUFFER_TTL_SECONDS)
        await redis.expire(seq_key, self.BUFFER_TTL_SECONDS)

    async def list_pending_chats(self) -> list[int]:
        """Lista los chats con una lista de fragmentos viva en Redis.

        Se usa al arrancar para recuperar ráfagas sin esperar un mensaje nuevo.
        """
        redis = self._get_redis()
        prefix = self.MSG_BUFFER_PREFIX
        chats: set[int] = set()

        async for key in redis.scan_iter(match=f"{prefix}*"):
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            suffix = key_str[len(prefix) :]
            try:
                chats.add(int(suffix))
            except ValueError:
                logger.warning("Clave de buffer no reconocida: %s", key_str)

        return sorted(chats)

    async def ensure_sequence(self, chat_id: str) -> int:
        """Recupera la secuencia y la crea si el contador expiró antes que la lista."""
        current_seq = await self.get_current_sequence(chat_id)
        if current_seq > 0:
            return current_seq

        redis = self._get_redis()
        seq_key = f"{self.SEQ_COUNTER_PREFIX}{chat_id}"
        created = await redis.set(seq_key, 1, nx=True, ex=self.BUFFER_TTL_SECONDS)
        if created:
            return 1
        return await self.get_current_sequence(chat_id)

    async def extend_pending_ttl(
        self, ttl_seconds: int = SHUTDOWN_RECOVERY_TTL_SECONDS
    ) -> int:
        """Extiende el TTL de los buffers vivos para el próximo arranque.

        Solo cubre un apagado ordenado; un SIGKILL deja el TTL normal de 60 s.
        """
        redis = self._get_redis()
        chats = await self.list_pending_chats()
        for chat_id in chats:
            await redis.expire(f"{self.MSG_BUFFER_PREFIX}{chat_id}", ttl_seconds)
            await redis.expire(f"{self.SEQ_COUNTER_PREFIX}{chat_id}", ttl_seconds)
        return len(chats)

    async def get_current_sequence(self, chat_id: str) -> int:
        """Retorna la secuencia actual sin modificarla."""
        redis = self._get_redis()
        seq_key = f"{self.SEQ_COUNTER_PREFIX}{chat_id}"
        val = await redis.get(seq_key)
        if val is None:
            return 0
        return int(val)

    async def flush_all(self, chat_id: str) -> list[dict[str, Any]]:
        """Recupera todos los eventos acumulados y limpia el buffer."""
        redis = self._get_redis()
        buffer_key = f"{self.MSG_BUFFER_PREFIX}{chat_id}"
        seq_key = f"{self.SEQ_COUNTER_PREFIX}{chat_id}"

        # Recuperar todos
        raw_events = await redis.lrange(buffer_key, 0, -1)

        # Limpiar
        await redis.delete(buffer_key)
        await redis.delete(seq_key)

        events = []
        for re in raw_events:
            if isinstance(re, bytes):
                re = re.decode("utf-8")
            events.append(json.loads(re))

        return events


# Instancia singleton
ingestion_buffer = IngestionBuffer()
