"""Recuperación de ráfagas que quedaron en Redis al apagar AEGEN."""

import asyncio
import logging
from uuid import uuid4

from src.api.services.debounce_manager import process_buffered_events
from src.core import dependencies
from src.core.ingestion_buffer import ingestion_buffer

logger = logging.getLogger(__name__)

# Tareas de recuperación vivas; se cancelan en el apagado ordenado.
_startup_recovery_tasks: set[asyncio.Task[None]] = set()


def _on_recovery_done(task: asyncio.Task[None]) -> None:
    """Retira la tarea y registra fallos que no llegaron a capturarse."""
    _startup_recovery_tasks.discard(task)
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error("Fallo en la recuperación de un buffer.", exc_info=error)


async def recover_pending_buffers() -> int:
    """Programa el procesamiento de los buffers que sobrevivieron al apagado.

    No espera un mensaje nuevo. Devuelve cuántos chats se programaron. La
    recuperación solo alcanza claves que sigan vivas en Redis; el apagado
    ordenado extiende su TTL para dar una ventana de reinicio.
    """
    if dependencies.redis_connection is None:
        logger.info("Redis no disponible; no hay buffers que recuperar.")
        return 0

    try:
        chats = await ingestion_buffer.list_pending_chats()
    except Exception:
        logger.exception("No se pudieron listar los buffers pendientes.")
        return 0

    scheduled = 0
    for chat_id in chats:
        try:
            task_seq = await ingestion_buffer.ensure_sequence(str(chat_id))
            if task_seq <= 0:
                logger.warning(
                    "Buffer del chat %s sin secuencia recuperable; se omite.",
                    chat_id,
                )
                continue

            try:
                await ingestion_buffer.refresh_ttl(str(chat_id))
            except Exception as e:
                logger.debug(
                    "No se pudo renovar el TTL del buffer del chat %s: %s",
                    chat_id,
                    e,
                )

            task = asyncio.create_task(
                process_buffered_events(
                    chat_id,
                    task_seq,
                    f"startup-{uuid4().hex[:12]}",
                )
            )
            _startup_recovery_tasks.add(task)
            task.add_done_callback(_on_recovery_done)
            scheduled += 1
        except Exception:
            logger.exception(
                "No se pudo programar la recuperación del chat %s.", chat_id
            )

    logger.info("Recuperación de arranque: %d chat(s) con buffer pendiente.", scheduled)
    return scheduled


async def cancel_startup_recovery_tasks() -> None:
    """Cancela las recuperaciones en curso durante el apagado ordenado."""
    tasks = [task for task in _startup_recovery_tasks if not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=5.0
            )
        except TimeoutError:
            logger.warning(
                "Algunas recuperaciones de arranque no terminaron en 5 s; "
                "los mensajes pendientes permanecen en el buffer."
            )
        logger.info("Canceladas %d recuperaciones de arranque pendientes.", len(tasks))
