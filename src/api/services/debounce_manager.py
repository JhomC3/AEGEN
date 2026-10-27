"""Debounce por chat y flujo de consolidación de una ráfaga.

La espera y los reintentos del cerrojo viven en ``lock_wait``; la adquisición
atómica y el latido viven en ``processing_lock``. Este módulo conserva el punto
de entrada público ``process_buffered_events`` y el flujo de la ráfaga.
"""

import asyncio
import logging
from contextlib import suppress
from datetime import datetime
from uuid import uuid4

from src.api.routers.privacy import handle_privacy_command, is_privacy_command
from src.api.services import lock_wait, processing_lock
from src.api.services.event_processor import process_event_task
from src.api.services.fragment_consolidator import consolidate_fragments
from src.core import schemas
from src.core.config import settings
from src.core.ingestion_buffer import ingestion_buffer
from src.tools import telegram_interface

logger = logging.getLogger(__name__)


async def _check_debounce(chat_id: int, task_seq: int) -> bool:
    """Verifica si la tarea actual es la más reciente."""
    current_seq = await ingestion_buffer.get_current_sequence(str(chat_id))
    if current_seq != task_seq:
        logger.debug(f"Debounce: Seq {task_seq} != {current_seq}. Abortando.")
        return False
    return True


async def _handle_privacy_intercept(
    event: schemas.CanonicalEventV1, chat_id: int
) -> bool:
    """Maneja comandos de privacidad. Retorna True si se interceptó y manejó."""
    if is_privacy_command(event.content):
        response_text = await handle_privacy_command(str(event.content), str(chat_id))
        if response_text:
            await telegram_interface.reply_to_telegram_chat.ainvoke({
                "chat_id": str(chat_id),
                "text": response_text,
            })
            return True
    return False


async def process_buffered_events(chat_id: int, task_seq: int, trace_id: str) -> None:
    """
    Tarea de fondo que espera y consolida mensajes acumulados.
    Implementa lógica de Debounce y Cerrojo de procesamiento.
    """
    # 1. Esperar el tiempo de debounce configurado
    await asyncio.sleep(settings.MESSAGE_DEBOUNCE_SECONDS)

    # 2. Verificar si somos la tarea más reciente (Debounce)
    if not await _check_debounce(chat_id, task_seq):
        return

    # 3. Cerrojo de Procesamiento (Lock atómico, espera acotada y reintento)
    lock_token = await lock_wait.wait_for_processing_lock(chat_id)
    if lock_token is None:
        lock_wait.schedule_lock_retry(chat_id, task_seq, trace_id)
        return

    renew_task: asyncio.Task[None] | None = None
    if lock_token:
        renew_task = asyncio.create_task(
            processing_lock.keep_processing_lock_alive(chat_id, lock_token)
        )

    try:
        # Si mientras esperábamos llegó una tarea más nueva, esa tarea es la
        # responsable de consolidar; esta libera el cerrojo sin consumir.
        if not await _check_debounce(chat_id, task_seq):
            return

        # 4. Recuperar fragmentos (Flush)
        fragments = await ingestion_buffer.flush_all(str(chat_id))
        if not fragments:
            return

        # 5. Ejecución con Protección (Try/Finally)
        # Feedback visual
        await telegram_interface.telegram_manager.send_chat_action(
            str(chat_id), "typing"
        )
        logger.info(f"Consolidando {len(fragments)} mensajes para el chat {chat_id}.")

        content, file_id, language_code, first_name, event_type_val = (
            consolidate_fragments(fragments)
        )

        # Crear y procesar evento canónico
        event = schemas.CanonicalEventV1(
            event_id=uuid4(),
            event_type=event_type_val,
            source="telegram",
            chat_id=chat_id,
            user_id=chat_id,
            file_id=file_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            language_code=language_code,
            first_name=first_name,
            metadata={
                "trace_id": trace_id,
                "consolidated": True,
                "fragment_count": len(fragments),
            },
        )

        # Interceptar comandos de privacidad
        if await _handle_privacy_intercept(event, chat_id):
            return

        await process_event_task(event)

    except Exception as e:
        logger.error(f"Error procesando ráfaga para {chat_id}: {e}", exc_info=True)
    finally:
        if renew_task is not None:
            renew_task.cancel()
            with suppress(asyncio.CancelledError):
                await renew_task
        await processing_lock.release_processing_lock(chat_id, lock_token)


async def cancel_pending_lock_retries() -> None:
    """Mantiene el nombre público; delega en el módulo de espera."""
    await lock_wait.cancel_pending_lock_retries()
