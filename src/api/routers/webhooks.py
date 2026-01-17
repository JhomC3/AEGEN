# src/api/routers/webhooks.py
import logging
import tempfile
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, status

from src.agents.orchestrator.factory import master_orchestrator
from src.core import schemas
from src.core.middleware import correlation_id
from src.core.schemas import GraphStateV2
from src.core.session_manager import session_manager
from src.tools import telegram_interface

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_event_task(event: schemas.CanonicalEventV1):
    """
    Tarea de fondo que orquesta el flujo de procesamiento para un evento canónico.
    """
    task_id = event.event_id
    chat_id = str(event.chat_id)
    logger.info(f"[TaskID: {task_id}] Iniciando orquestación para chat {chat_id}.")

    # Cargar sesión existente o inicializar historial vacío
    existing_session = await session_manager.get_session(chat_id)
    if existing_session:
        logger.info(
            f"[TaskID: {task_id}] Memoria cargada: {len(existing_session['conversation_history'])} mensajes"
        )
        conversation_history = existing_session["conversation_history"]
    else:
        logger.info(f"[TaskID: {task_id}] Nueva sesión conversacional")
        conversation_history = []

    # Crear el estado inicial del grafo con el historial correcto
    initial_state = GraphStateV2(
        event=event,
        payload={},
        error_message=None,
        conversation_history=conversation_history,
        session_id=str(event.chat_id),  # Propagar session_id
    )
    final_state: dict

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"[TaskID: {task_id}] Directorio temporal creado: {temp_dir}")

            if event.file_id:
                if event.event_type == "audio":
                    audio_file_path = (
                        await telegram_interface.download_telegram_audio.ainvoke({
                            "file_id": event.file_id,
                            "destination_folder": str(temp_path),
                        })
                    )
                    initial_state["payload"]["audio_file_path"] = audio_file_path
                    logger.info(
                        f"[TaskID: {task_id}] Audio descargado en {audio_file_path}"
                    )
                elif event.event_type == "image":
                    # Usamos la misma lógica de descarga pero para imágenes
                    image_file_path = (
                        await telegram_interface.download_telegram_audio.ainvoke({
                            "file_id": event.file_id,
                            "destination_folder": str(temp_path),
                        })
                    )
                    initial_state["payload"]["image_file_path"] = image_file_path
                    logger.info(
                        f"[TaskID: {task_id}] Imagen descargada en {image_file_path}"
                    )

            logger.info(f"[TaskID: {task_id}] Invocando al MasterOrchestrator.")
            final_state = await master_orchestrator.run(initial_state)

    except Exception as e:
        logger.error(
            f"[TaskID: {task_id}] Fallo no controlado en la orquestación: {e}",
            exc_info=True,
        )
        final_state = dict(initial_state)  # Convertir a dict genérico
        final_state["error_message"] = (
            "Ocurrió un error inesperado al procesar tu solicitud."
        )

    if final_state.get("error_message"):
        message = final_state["error_message"]
    else:
        response_content = final_state.get("payload", {}).get("response")
        message = (
            str(response_content)
            if response_content
            else "La tarea se completó, pero no se generó una respuesta."
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

    logger.info(f"[TaskID: {task_id}] Orquestación finalizada.")


@router.post(
    "/telegram",
    response_model=schemas.IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook for Telegram events",
    description="Receives events (like audio messages) forwarded from a Telegram bot.",
)
async def telegram_webhook(
    request: schemas.TelegramUpdate,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint que actúa como un 'Adaptador de Telegram'.
    """
    trace_id = correlation_id.get()

    if not request.message:
        logger.warning(
            f"Webhook de Telegram recibido sin contenido de mensaje. UpdateID: {request.update_id}"
        )
        return schemas.IngestionResponse(
            task_id=str(uuid4()),
            message="Event received but no processable content found.",
        )

    # Determinar el tipo de evento y el contenido
    event_type: Literal["text", "audio", "document", "unknown"] = "unknown"
    content: str | None = None
    file_id: str | None = None

    if request.message.voice:
        event_type = "audio"
        file_id = request.message.voice.file_id
    elif request.message.photo:
        event_type = "image"
        # Tomar la foto de mayor resolución (última en la lista)
        file_id = request.message.photo[-1].file_id
        content = request.message.caption  # Las fotos pueden tener caption
    elif request.message.text:
        event_type = "text"
        content = request.message.text

    # Si no se pudo determinar un tipo de evento procesable, no continuar.
    if event_type == "unknown":
        logger.warning(
            f"Webhook de Telegram recibido sin contenido procesable (ni voz ni texto). UpdateID: {request.update_id}"
        )
        return schemas.IngestionResponse(
            task_id=str(uuid4()),
            message="Event received but no processable content found.",
        )

    from datetime import datetime

    event = schemas.CanonicalEventV1(
        event_id=uuid4(),
        event_type=event_type,
        source="telegram",
        chat_id=request.message.chat.id,
        user_id=request.message.chat.id,
        file_id=file_id,
        content=content,
        timestamp=datetime.now().isoformat(),
        metadata={"trace_id": trace_id, "update_id": request.update_id},
    )
    logger.info(
        f"Webhook de Telegram recibido. EventID: {event.event_id}, TraceID: {trace_id}"
    )

    background_tasks.add_task(process_event_task, event)

    return schemas.IngestionResponse(
        task_id=str(event.event_id), message="Telegram event accepted for processing."
    )
