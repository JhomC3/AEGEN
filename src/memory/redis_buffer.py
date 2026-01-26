import json
import logging
import time
from typing import Any

from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisMessageBuffer:
    """
    Gestión de buffer de mensajes en Redis (Diskless).
    Implementa almacenamiento temporal de conversaciones antes de la consolidación.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self.PREFIX = "chat:buffer:"
        self.ACTIVITY_PREFIX = "chat:last_activity:"

    async def push_message(self, chat_id: str, role: str, content: str):
        """Añade un mensaje al buffer de Redis."""
        key = f"{self.PREFIX}{chat_id}"
        message = {"role": role, "content": content, "timestamp": time.time()}
        payload = json.dumps(message, ensure_ascii=False)

        # RPUSH añade al final de la lista
        await self._redis.rpush(key, payload)
        await self.update_last_activity(chat_id)

        # Mantener un límite de seguridad de 50 mensajes
        await self._redis.ltrim(key, -50, -1)
        logger.debug(f"Mensaje pusheado a Redis para {chat_id}")

    async def get_messages(self, chat_id: str) -> list[dict[str, Any]]:
        """Recupera todos los mensajes del buffer."""
        key = f"{self.PREFIX}{chat_id}"
        raw_messages = await self._redis.lrange(key, 0, -1)

        messages = []
        for rm in raw_messages:
            try:
                # Decodificar si vienen como bytes (decode_responses=False)
                if isinstance(rm, bytes):
                    rm = rm.decode("utf-8")
                messages.append(json.loads(rm))
            except Exception as e:
                logger.error(f"Error decodificando mensaje de Redis: {e}")

        return messages

    async def clear_buffer(self, chat_id: str):
        """Elimina el buffer de mensajes de Redis."""
        key = f"{self.PREFIX}{chat_id}"
        await self._redis.delete(key)
        logger.info(f"Buffer limpiado en Redis para {chat_id}")

    async def get_message_count(self, chat_id: str) -> int:
        """Retorna la cantidad de mensajes en el buffer."""
        key = f"{self.PREFIX}{chat_id}"
        return await self._redis.llen(key)

    async def update_last_activity(self, chat_id: str):
        """Actualiza el timestamp de última actividad."""
        key = f"{self.ACTIVITY_PREFIX}{chat_id}"
        await self._redis.set(key, str(time.time()))

    async def get_last_activity(self, chat_id: str) -> float:
        """Obtiene el timestamp de última actividad."""
        key = f"{self.ACTIVITY_PREFIX}{chat_id}"
        val = await self._redis.get(key)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            try:
                return float(val)
            except ValueError:
                return 0.0
        return 0.0
