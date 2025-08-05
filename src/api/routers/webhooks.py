# src/api/routers/webhooks.py
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from src.core.dependencies import get_event_bus
from src.core.interfaces.bus import IEventBus
from src.core.middleware import correlation_id
from src.core.schemas import IngestionResponse, TelegramWebhookRequest

router = APIRouter()
logger = logging.getLogger(__name__)

event_bus_dependency = Depends(get_event_bus)


@router.post(
    "/telegram",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook for Telegram events",
    description="Receives events (like audio messages) forwarded from a Telegram bot.",
)
async def telegram_webhook(
    request: TelegramWebhookRequest,
    event_bus: IEventBus = event_bus_dependency,
):
    """
    Endpoint para recibir y procesar eventos de Telegram.

    Actualmente, está diseñado para manejar el workflow 'audio_transcription'.
    """
    task_id = str(uuid4())
    trace_id = correlation_id.get()
    logger.info(
        f"Received Telegram webhook request for task '{request.task_name}'. Assigning TaskID: {task_id}"
    )

    # Construir el evento para el bus a partir de la petición del webhook
    event = {
        "task_id": task_id,
        "trace_id": trace_id,
        "task_name": request.task_name,
        "chat_id": request.payload.chat_id,
        "file_id": request.payload.file_id,
    }

    await event_bus.publish("workflow_tasks", event)
    logger.info(f"Task {task_id} published to 'workflow_tasks' topic.")

    return IngestionResponse(
        task_id=task_id, message="Telegram event accepted for processing."
    )
