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

    def __init__(self):
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
        await redis.expire(buffer_key, 60)
        await redis.expire(seq_key, 60)

        logger.debug(
            f"Event pushed to ingestion buffer for {chat_id}. Seq: {current_seq}"
        )
        return current_seq

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
