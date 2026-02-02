# src/api/routers/webhooks.py
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, status

from src.agents.orchestrator.factory import master_orchestrator
from src.core import schemas
from src.core.ingestion_buffer import ingestion_buffer
from src.core.middleware import correlation_id
from src.core.schemas import GraphStateV2
from src.core.session_manager import session_manager
from src.tools import telegram_interface

router = APIRouter()
logger = logging.getLogger(__name__)


async def _download_event_files(
    event: schemas.CanonicalEventV1, temp_path: Path
) -> dict[str, Any]:
    """Descarga archivos (audio/imagen) del evento si existen."""
    payload_updates = {}
    if event.file_id:
        if event.event_type == "audio":
            audio_file_path = await telegram_interface.download_telegram_audio.ainvoke({
                "file_id": event.file_id,
                "destination_folder": str(temp_path),
            })
            payload_updates["audio_file_path"] = audio_file_path
            logger.info(f"Audio descargado en {audio_file_path}")
        elif event.event_type == "image":
            image_file_path = await telegram_interface.download_telegram_audio.ainvoke({
                "file_id": event.file_id,
                "destination_folder": str(temp_path),
            })
            payload_updates["image_file_path"] = image_file_path
            logger.info(f"Imagen descargada en {image_file_path}")
    return payload_updates


async def process_event_task(event: schemas.CanonicalEventV1):
    """
    Tarea de fondo que orquesta el flujo de procesamiento para un evento canónico.
    """
    task_id = event.event_id
    chat_id = str(event.chat_id)
    logger.info(f"[TaskID: {task_id}] Iniciando orquestación para chat {chat_id}.")

    # C.9: Actualizar localización antes de procesar
    if event.language_code:
        from src.core.profile_manager import user_profile_manager

        await user_profile_manager.update_localization(chat_id, event.language_code)

    # Cargar sesión existente o inicializar historial vacío
    existing_session = await session_manager.get_session(chat_id)
    payload = {}
    conversation_history = []
    if existing_session:
        logger.info(
            f"[TaskID: {task_id}] Memoria cargada: {len(existing_session['conversation_history'])} mensajes. "
            f"Last Specialist: {existing_session.get('last_specialist')}"
        )
        conversation_history = existing_session["conversation_history"]
        # Inyectar contexto previo para el RoutingAnalyzer
        payload = {
            "last_specialist": existing_session.get("last_specialist"),
            "last_intent": existing_session.get("last_intent"),
            "session_context": existing_session.get("session_context", {}),
        }
    else:
        logger.info(f"[TaskID: {task_id}] Nueva sesión conversacional")

    # Crear el estado inicial del grafo
    initial_state = GraphStateV2(
        event=event,
        payload=payload,
        error_message=None,
        conversation_history=conversation_history,
        session_id=str(event.chat_id),
    )
    final_state: dict

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"[TaskID: {task_id}] Directorio temporal creado: {temp_dir}")

            file_payload = await _download_event_files(event, temp_path)
            initial_state["payload"].update(file_payload)

            logger.info(f"[TaskID: {task_id}] Invocando al MasterOrchestrator.")
            final_state = await master_orchestrator.run(initial_state)

    except Exception as e:
        logger.error(
            f"[TaskID: {task_id}] Fallo no controlado en la orquestación: {e}",
            exc_info=True,
        )
        final_state = dict(initial_state)
        final_state["error_message"] = (
            "Ocurrió un error inesperado al procesar tu solicitud."
        )

    response_content = final_state.get("payload", {}).get("response")
    message = (
        final_state.get("error_message") or str(response_content)
        if response_content and str(response_content).strip()
        else "La tarea se completó, pero el agente generó una respuesta vacía."
    )

    logger.info(f"[TaskID: {task_id}] Enviando respuesta al chat {chat_id}.")
    try:
        await telegram_interface.reply_to_telegram_chat.ainvoke({
            "chat_id": chat_id,
            "message": message,
        })
    except Exception as e:
        logger.error(f"[TaskID: {task_id}] Error enviando respuesta a Telegram: {e}")

    # Guardar el estado actualizado de la sesión en Redis
    session_saved = await session_manager.save_session(chat_id, final_state)
    if session_saved:
        history_len = len(final_state.get("conversation_history", []))
        logger.info(f"[TaskID: {task_id}] Memoria guardada: {history_len} mensajes")
    else:
        logger.warning(f"[TaskID: {task_id}] Fallo al guardar memoria conversacional")

    # PHASE 1: Connect the Broken Link (Buffer para consolidación en Google Cloud)
    try:
        from src.memory.long_term_memory import long_term_memory

        # 1. Guardar mensaje del usuario
        user_content = event.content or "[Contenido no textual]"
        await long_term_memory.store_raw_message(chat_id, "user", user_content)

        # 2. Guardar respuesta del asistente
        await long_term_memory.store_raw_message(chat_id, "assistant", message)

        logger.info(
            f"[TaskID: {task_id}] Mensajes enviados al buffer de consolidación."
        )
    except Exception as e:
        logger.error(
            f"[TaskID: {task_id}] Error al enviar mensajes al buffer de consolidación: {e}"
        )

    logger.info(f"[TaskID: {task_id}] Orquestación finalizada.")


def _consolidate_fragments(
    fragments: list[dict],
) -> tuple[
    str | None,
    str | None,
    str | None,
    Literal["text", "audio", "document", "image", "unknown"],
]:
    """
    Consolida fragmentos de mensajes en contenido y metadatos únicos.
    """
    combined_content = []
    final_file_id = None
    final_language_code = None
    final_event_type: Literal["text", "audio", "document", "image", "unknown"] = "text"

    for frag in fragments:
        if frag.get("content"):
            combined_content.append(frag["content"])
        if not final_language_code and frag.get("language_code"):
            final_language_code = frag["language_code"]

        # Prioridad de tipos
        if frag.get("event_type") == "audio":
            final_file_id = frag.get("file_id")
            final_event_type = "audio"
        elif frag.get("event_type") == "image" and final_event_type != "audio":
            final_file_id = frag.get("file_id")
            final_event_type = "image"

    content = "\n".join(combined_content) if combined_content else None
    return content, final_file_id, final_language_code, final_event_type


async def process_buffered_events(chat_id: int, task_seq: int, trace_id: str):
    """
    Tarea de fondo que espera y consolida mensajes acumulados.
    Implementa lógica de Debounce y Cerrojo de procesamiento.
    """
    # 1. Esperar el tiempo de debounce
    await asyncio.sleep(3.0)

    # 2. Verificar si somos la tarea más reciente (Debounce)
    current_seq = await ingestion_buffer.get_current_sequence(str(chat_id))
    if current_seq != task_seq:
        logger.debug(f"Debounce: Seq {task_seq} != {current_seq}. Abortando.")
        return

    # 3. Cerrojo de Procesamiento (Lock)
    from src.core.dependencies import redis_connection

    lock_key = f"lock:processing:{chat_id}"

    if redis_connection:
        is_processing = await redis_connection.get(lock_key)
        if is_processing:
            logger.info(f"Chat {chat_id} ocupado. Esperando ráfaga tardía...")
            await asyncio.sleep(2.0)
            # Re-verificar debounce tras la espera
            current_seq = await ingestion_buffer.get_current_sequence(str(chat_id))
            if current_seq != task_seq:
                return

    # 4. Recuperar fragmentos (Flush)
    fragments = await ingestion_buffer.flush_all(str(chat_id))
    if not fragments:
        return

    # 5. Ejecución con Protección (Try/Finally)
    if redis_connection:
        await redis_connection.setex(lock_key, 60, "true")

    try:
        # Feedback visual
        await telegram_interface.telegram_manager.send_chat_action(
            str(chat_id), "typing"
        )
        logger.info(f"Consolidando {len(fragments)} mensajes para el chat {chat_id}.")

        content, file_id, language_code, event_type_val = _consolidate_fragments(
            fragments
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
            metadata={
                "trace_id": trace_id,
                "consolidated": True,
                "fragment_count": len(fragments),
            },
        )

        await process_event_task(event)

    except Exception as e:
        logger.error(f"Error procesando ráfaga para {chat_id}: {e}", exc_info=True)
    finally:
        if redis_connection:
            await redis_connection.delete(lock_key)


@router.post(
    "/telegram",
    response_model=schemas.IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook for Telegram events",
    description="Receives events forwarded from a Telegram bot and implements dynamic debounce.",
)
async def telegram_webhook(
    request: schemas.TelegramUpdate,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint que actúa como un 'Adaptador de Telegram' con acumulación.
    """
    trace_id = correlation_id.get()

    if not request.message:
        return schemas.IngestionResponse(
            task_id=str(uuid4()),
            message="Event received but no processable content found.",
        )

    # Determinar el tipo de evento y el contenido
    event_type: Literal["text", "audio", "document", "image", "unknown"] = "unknown"
    content: str | None = None
    file_id: str | None = None

    if request.message.voice:
        event_type = "audio"
        file_id = request.message.voice.file_id
    elif request.message.photo:
        event_type = "image"
        file_id = request.message.photo[-1].file_id
        content = request.message.caption
    elif request.message.text:
        event_type = "text"
        content = request.message.text

    if event_type == "unknown":
        return schemas.IngestionResponse(
            task_id=str(uuid4()),
            message="Event received but no processable content found.",
        )

    chat_id = request.message.chat.id

    # 1. Guardar fragmento en el buffer
    # C.8: Extraer metadatos de localización del usuario
    language_code = None
    if request.message and request.message.from_user:
        language_code = request.message.from_user.language_code

    fragment_data = {
        "event_type": event_type,
        "content": content,
        "file_id": file_id,
        "language_code": language_code,
    }
    current_seq = await ingestion_buffer.push_event(str(chat_id), fragment_data)

    # 2. Feedback inmediato al usuario
    # Determinamos la acción según el tipo de mensaje predominante
    action = "record_voice" if event_type == "audio" else "typing"
    background_tasks.add_task(
        telegram_interface.telegram_manager.send_chat_action, str(chat_id), action
    )

    # 3. Lanzar tarea de fondo con espera
    background_tasks.add_task(
        process_buffered_events, chat_id, current_seq, trace_id or "no-trace"
    )

    return schemas.IngestionResponse(
        task_id=f"{chat_id}-{current_seq}",
        message="Telegram event accepted and buffered.",
    )
