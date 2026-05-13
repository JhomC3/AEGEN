import logging
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import BackgroundTasks

from src.api.services.debounce_manager import process_buffered_events
from src.core import schemas
from src.core.ingestion_buffer import ingestion_buffer
from src.core.interfaces.channel import IChannel
from src.core.schemas.graph import CanonicalEventV1
from src.tools import telegram_interface

logger = logging.getLogger(__name__)


class TelegramChannel(IChannel):
    """Implementación del canal de Telegram."""

    @property
    def channel_type(self) -> str:
        return "telegram"

    async def send_response(self, chat_id: str, text: str, **kwargs: Any) -> bool:
        """Envía un mensaje a Telegram usando el manager existente."""
        return await telegram_interface.telegram_manager.send_message(chat_id, text)

    async def process_event(self, event: CanonicalEventV1) -> Any:
        """
        Este método será el puente hacia el MasterOrchestrator en el futuro.
        Por ahora, la lógica de orquestación vive en el debounce_manager.
        """
        # TODO: Mover lógica de process_buffered_events aquí para centralizar
        pass


async def process_telegram_update(
    request: schemas.TelegramUpdate,
    background_tasks: BackgroundTasks,
    trace_id: str,
) -> schemas.IngestionResponse:
    """
    Procesa un update de Telegram: clasifica, checkea latencia y encola con debounce.
    Mantenido por compatibilidad con el endpoint de Webhook actual.
    """
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

    # C.8: Extraer metadatos de localización del usuario
    language_code = None
    first_name = None
    if request.message and request.message.from_user:
        language_code = request.message.from_user.language_code
        first_name = request.message.from_user.first_name

    # Diagnóstico de Latencia de Red
    try:
        msg_date_timestamp = getattr(request.message, "date", None)
        if msg_date_timestamp is not None:
            msg_date = datetime.fromtimestamp(float(msg_date_timestamp))
            now = datetime.now()
            latency = (now - msg_date).total_seconds()
            if latency > 5.0:
                logger.warning("ALTA LATENCIA Telegram: %.2fs", latency)
    except Exception as e:
        logger.debug("Error calculando latencia Telegram: %s", e)

    fragment_data = {
        "event_type": event_type,
        "content": content,
        "file_id": file_id,
        "language_code": language_code,
        "first_name": first_name,
    }
    current_seq = await ingestion_buffer.push_event(str(chat_id), fragment_data)

    # Feedback inmediato
    action = "record_voice" if event_type == "audio" else "typing"
    background_tasks.add_task(
        telegram_interface.telegram_manager.send_chat_action, str(chat_id), action
    )

    # Procesamiento con debounce
    background_tasks.add_task(
        process_buffered_events, chat_id, current_seq, trace_id or "no-trace"
    )

    return schemas.IngestionResponse(
        task_id=f"{chat_id}-{current_seq}",
        message="Telegram event accepted and buffered.",
    )
