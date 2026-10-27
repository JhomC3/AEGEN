"""Espera acotada del cerrojo y reintentos que no consumen la ráfaga."""

import asyncio
import logging

from src.api.services import processing_lock

logger = logging.getLogger(__name__)

# Espera entre intentos cuando otra tarea del mismo chat tiene el cerrojo.
LOCK_RETRY_INTERVAL_SECONDS = 0.25
# Límite de una espera continua. Al vencer se reprograma la ráfaga.
LOCK_WAIT_TIMEOUT_SECONDS = 30.0
# Retardo antes de reintentar una ráfaga que agotó su espera.
LOCK_RETRY_DELAY_SECONDS = 2.0
# Tareas de reintento vivas; se cancelan en el apagado de la aplicación.
_pending_lock_retries: set[asyncio.Task[None]] = set()
# Una vez iniciado el apagado no se programan reintentos nuevos.
_shutting_down = False


async def wait_for_processing_lock(chat_id: int) -> str | None:
    """Espera acotada por el cerrojo; no descarta la ráfaga.

    Devuelve el token si lo adquiere, cadena vacía si no hay Redis (degradación
    existente) o ``None`` si vence ``LOCK_WAIT_TIMEOUT_SECONDS``. En este último
    caso el llamador debe reprogramar; el buffer no se toca.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + LOCK_WAIT_TIMEOUT_SECONDS
    logged_wait = False
    logged_error = False

    while True:
        try:
            token = await processing_lock.acquire_processing_lock(chat_id)
        except Exception as e:
            # No se procesa sin cerrojo ante un error transitorio: se reintenta
            # hasta el límite y luego se reprograma.
            token = None
            if not logged_error:
                logger.warning(
                    "Error adquiriendo el cerrojo del chat %s; se reintenta: %s",
                    chat_id,
                    e,
                )
                logged_error = True

        if token is not None:
            return token

        if not logged_wait:
            logger.info(
                "Chat %s ocupado; la ráfaga espera su turno (no se descarta).",
                chat_id,
            )
            logged_wait = True

        await processing_lock.refresh_buffer_ttl(chat_id)
        remaining = deadline - loop.time()
        if remaining <= 0:
            logger.warning(
                "Espera de cerrojo agotada para el chat %s tras %.0f s; "
                "se reprograma la ráfaga sin consumir el buffer.",
                chat_id,
                LOCK_WAIT_TIMEOUT_SECONDS,
            )
            return None

        await asyncio.sleep(min(LOCK_RETRY_INTERVAL_SECONDS, remaining))


async def _retry_processing_after_lock_timeout(
    chat_id: int, task_seq: int, trace_id: str
) -> None:
    """Reprograma una ráfaga que agotó la espera del cerrojo.

    No consume el buffer. Al despertar vuelve a intentar el flujo completo; si
    sigue ocupado, se reprograma otra vez. Así el mensaje no depende de que el
    usuario envíe uno nuevo.
    """
    from src.api.services.debounce_manager import process_buffered_events

    try:
        await asyncio.sleep(LOCK_RETRY_DELAY_SECONDS)
        await process_buffered_events(chat_id, task_seq, trace_id)
    except asyncio.CancelledError:
        logger.info(
            "Reintento de cerrojo cancelado para el chat %s; "
            "los mensajes permanecen en el buffer.",
            chat_id,
        )
        raise
    except Exception:
        logger.exception("Error en el reintento de cerrojo para el chat %s", chat_id)


def schedule_lock_retry(chat_id: int, task_seq: int, trace_id: str) -> None:
    """Registra el reintento para poder cancelarlo en el apagado."""
    if _shutting_down:
        logger.info(
            "Apagado en curso; no se reprograma el chat %s. "
            "Los mensajes permanecen en el buffer.",
            chat_id,
        )
        return
    try:
        task = asyncio.create_task(
            _retry_processing_after_lock_timeout(chat_id, task_seq, trace_id)
        )
    except RuntimeError as e:
        # Sin event loop vivo (apagado en curso) no se puede reprogramar; el
        # buffer conserva los mensajes para el próximo arranque.
        logger.error(
            "No se pudo programar el reintento del chat %s; "
            "los mensajes permanecen en el buffer: %s",
            chat_id,
            e,
        )
        return
    _pending_lock_retries.add(task)
    task.add_done_callback(_pending_lock_retries.discard)
    logger.info(
        "Reintento de cerrojo programado para el chat %s en %.0f s.",
        chat_id,
        LOCK_RETRY_DELAY_SECONDS,
    )


async def cancel_pending_lock_retries() -> None:
    """Cancela los reintentos pendientes durante el apagado ordenado."""
    global _shutting_down
    _shutting_down = True
    tasks = [task for task in _pending_lock_retries if not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=5.0
            )
        except TimeoutError:
            logger.warning(
                "Algunos reintentos de cerrojo no terminaron en 5 s; "
                "los mensajes permanecen en el buffer."
            )
        logger.info("Cancelados %d reintentos de cerrojo pendientes.", len(tasks))
