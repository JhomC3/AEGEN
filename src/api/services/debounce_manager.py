import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from src.api.routers.privacy import handle_privacy_command, is_privacy_command
from src.api.services.event_processor import process_event_task
from src.api.services.fragment_consolidator import consolidate_fragments
from src.core import dependencies, schemas
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


async def _wait_for_lock(chat_id: int, task_seq: int, lock_key: str) -> bool:
    """Espera si el chat está ocupado y re-verifica debounce."""
    if not dependencies.redis_connection:
        return True

    is_processing = await dependencies.redis_connection.get(lock_key)
    if is_processing:
        logger.info(f"Chat {chat_id} ocupado. Esperando ráfaga tardía...")
        await asyncio.sleep(2.0)
        # Re-verificar debounce tras la espera
        return await _check_debounce(chat_id, task_seq)

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
                "message": response_text,
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

    # 3. Cerrojo de Procesamiento (Lock)
    lock_key = f"lock:processing:{chat_id}"
    if not await _wait_for_lock(chat_id, task_seq, lock_key):
        return

    # 4. Recuperar fragmentos (Flush)
    fragments = await ingestion_buffer.flush_all(str(chat_id))
    if not fragments:
        return

    # 5. Ejecución con Protección (Try/Finally)
    if dependencies.redis_connection:
        await dependencies.redis_connection.setex(lock_key, 60, "true")

    try:
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
        if dependencies.redis_connection:
            await dependencies.redis_connection.delete(lock_key)
