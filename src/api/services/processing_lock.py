"""Cerrojo Redis por chat: adquisición, renovación y liberación.

Este módulo no conoce la ráfaga ni el debounce; solo garantiza que una tarea
del mismo chat posea el cerrojo mientras procesa.
"""

import asyncio
import logging
from uuid import uuid4

from src.core import dependencies
from src.core.ingestion_buffer import ingestion_buffer

logger = logging.getLogger(__name__)

PROCESSING_LOCK_TTL_SECONDS = 60
# El cerrojo se renueva mientras la tarea sigue viva; el TTL es solo la red de
# seguridad si el proceso muere. Renovar cada TTL/3 deja dos oportunidades antes
# de que expire por un fallo transitorio de Redis o del event loop.
LOCK_RENEW_INTERVAL_SECONDS = PROCESSING_LOCK_TTL_SECONDS / 3

RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""
RENEW_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""


def _processing_lock_key(chat_id: int) -> str:
    """Clave del cerrojo de procesamiento por chat."""
    return f"lock:processing:{chat_id}"


async def acquire_processing_lock(chat_id: int) -> str | None:
    """Adquiere el cerrojo de forma atómica.

    Devuelve el token de propiedad, ``None`` si otra tarea lo tiene, o cadena
    vacía si no hay Redis (degradación sin cerrojo).
    """
    redis_client = dependencies.redis_connection
    if redis_client is None:
        return ""

    token = uuid4().hex
    acquired = await redis_client.set(
        _processing_lock_key(chat_id),
        token,
        nx=True,
        ex=PROCESSING_LOCK_TTL_SECONDS,
    )
    return token if acquired else None


async def renew_processing_lock(chat_id: int, token: str) -> bool:
    """Renueva el TTL solo si el cerrojo sigue siendo de esta tarea."""
    if not token:
        return False
    redis_client = dependencies.redis_connection
    if redis_client is None:
        return False

    renewed = await redis_client.eval(
        RENEW_LOCK_SCRIPT,
        1,
        _processing_lock_key(chat_id),
        token,
        int(PROCESSING_LOCK_TTL_SECONDS),
    )
    return bool(renewed)


async def keep_processing_lock_alive(chat_id: int, token: str) -> None:
    """Renueva el cerrojo periódicamente mientras la tarea lo posea.

    Si se pierde la propiedad, se registra y se deja de renovar: otra tarea
    pudo haber tomado el cerrojo tras una expiración. No se vuelve a adquirir
    aquí para no provocar dos procesamientos simultáneos.
    """
    while True:
        await asyncio.sleep(LOCK_RENEW_INTERVAL_SECONDS)
        try:
            renewed = await renew_processing_lock(chat_id, token)
        except Exception as e:
            logger.warning(
                "No se pudo renovar el cerrojo del chat %s; se deja expirar: %s",
                chat_id,
                e,
            )
            return
        if not renewed:
            logger.error(
                "Cerrojo del chat %s perdido durante el procesamiento; "
                "otra tarea pudo haberlo tomado.",
                chat_id,
            )
            return


async def refresh_buffer_ttl(chat_id: int) -> None:
    """Mantiene vivos los mensajes mientras la ráfaga espera el cerrojo."""
    refresh = getattr(ingestion_buffer, "refresh_ttl", None)
    if refresh is None:
        return
    try:
        await refresh(str(chat_id))
    except Exception as e:
        logger.debug("No se pudo renovar el TTL del buffer del chat %s: %s", chat_id, e)


async def release_processing_lock(chat_id: int, token: str) -> None:
    """Libera el cerrojo solo si pertenece a esta tarea."""
    if not token:
        return
    redis_client = dependencies.redis_connection
    if redis_client is None:
        return

    try:
        await redis_client.eval(
            RELEASE_LOCK_SCRIPT,
            1,
            _processing_lock_key(chat_id),
            token,
        )
    except Exception as e:
        # El TTL libera el cerrojo; nunca borrar el de otra tarea a ciegas.
        logger.warning("No se pudo liberar el cerrojo del chat %s: %s", chat_id, e)
