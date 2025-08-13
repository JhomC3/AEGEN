# src/api/routers/webhooks.py
import logging
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, status

from src.agents.specialists.transcription_agent import transcription_agent
from src.core import schemas
from src.core.middleware import correlation_id
from src.tools import telegram_interface

router = APIRouter()
logger = logging.getLogger(__name__)


async def transcription_task(event: schemas.CanonicalEventV1):
    """
    Tarea de fondo que orquesta el flujo de transcripción para Telegram.
    Utiliza un directorio temporal para gestionar los archivos de forma segura.
    """
    task_id = event.event_id
    logger.info(
        f"[TaskID: {task_id}] Iniciando orquestación para chat {event.chat_id}."
    )

    # Inicializa el estado del grafo
    state = schemas.GraphStateV1(event=event, error_message=None)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"[TaskID: {task_id}] Directorio temporal creado: {temp_dir}")

            # 1. Descargar el audio al directorio temporal
            audio_file_path = await telegram_interface.download_telegram_audio.ainvoke(
                {
                    "file_id": event.file_id,
                    "destination_folder": str(temp_path),
                }
            )
            state.payload["audio_file_path"] = audio_file_path
            logger.info(f"[TaskID: {task_id}] Audio descargado en {audio_file_path}")

            # 2. Invocar al agente agnóstico de transcripción
            logger.info(f"[TaskID: {task_id}] Invocando al agente de transcripción.")
            final_state = await transcription_agent.run(state)

    except Exception as e:
        logger.error(
            f"[TaskID: {task_id}] Fallo no controlado en la orquestación: {e}",
            exc_info=True,
        )
        # Si la excepción ocurre fuera del agente, final_state no existirá.
        # Creamos un estado de error para notificar al usuario.
        final_state = schemas.GraphStateV1(
            event=event,
            error_message="Ocurrió un error inesperado al procesar tu audio.",
        )

    # 3. Enviar la respuesta final (éxito o error)
    if final_state.error_message:
        message = final_state.error_message
    else:
        transcription = (
            final_state.payload.get("transcription")
            or "No se pudo obtener la transcripción."
        )
        message = f"Transcripción:\n\n---\n\n{transcription}"

    logger.info(f"[TaskID: {task_id}] Enviando respuesta al chat {event.chat_id}.")
    await telegram_interface.reply_to_telegram_chat.ainvoke(
        {
            "chat_id": str(event.chat_id),
            "message": message,
        }
    )
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
    Convierte el evento de Telegram en un CanonicalEvent y lo encola para su procesamiento.
    """
    trace_id = correlation_id.get()

    # Validar que el mensaje contiene un audio
    if not request.message or not request.message.voice:
        logger.warning(
            f"Webhook de Telegram recibido sin mensaje de voz. UpdateID: {request.update_id}"
        )
        # Aún así devolvemos 202 para no alentar a Telegram a reintentar.
        return schemas.IngestionResponse(
            task_id=str(uuid4()),
            message="Event received but no voice message found to process.",
        )

    event = schemas.CanonicalEventV1(
        source="telegram",
        chat_id=request.message.chat.id,
        user_id=request.message.chat.id,  # Usando chat.id como user_id para Telegram
        file_id=request.message.voice.file_id,
        content=None,  # El contenido principal está en el archivo, no en un mensaje de texto
        metadata={"trace_id": trace_id, "update_id": request.update_id},
    )
    logger.info(
        f"Webhook de Telegram recibido. EventID: {event.event_id}, TraceID: {trace_id}"
    )

    # Encolar la tarea de orquestación completa en segundo plano
    background_tasks.add_task(transcription_task, event)

    return schemas.IngestionResponse(
        task_id=str(event.event_id), message="Telegram event accepted for processing."
    )
