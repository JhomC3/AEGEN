"""
Router para gestionar los webhooks de servicios externos, como Telegram.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.dependencies import get_event_bus
from src.core.interfaces.bus import IEventBus

logger = logging.getLogger(__name__)
router = APIRouter()

# Inyección de dependencias recomendada para evitar B008
EventBusDep = Annotated[IEventBus, Depends(get_event_bus)]


@router.post("/telegram", status_code=202)
async def handle_telegram_webhook(request: Request, event_bus: EventBusDep):
    """
    Endpoint para recibir actualizaciones del webhook de Telegram.

    Parsea la actualización, y si contiene un mensaje de audio,
    publica un evento para que el workflow de transcripción lo procese.
    """
    try:
        data = await request.json()
        logger.debug(f"Webhook de Telegram recibido: {data}")

        # Extraer el mensaje. Puede estar en 'message' o 'channel_post'.
        message = data.get("message") or data.get("channel_post")

        if message and "audio" in message:
            chat_id = message["chat"]["id"]
            file_id = message["audio"]["file_id"]

            # Crear el evento para el bus
            event = {
                "task_name": "audio_transcription",
                "chat_id": str(chat_id),
                "file_id": file_id,
            }

            # Publicar el evento
            await event_bus.publish("workflow_events", event)
            logger.info(
                f"Evento 'audio_transcription' publicado para el chat_id {chat_id}."
            )
            return {"status": "evento publicado"}

        logger.info(
            "Webhook de Telegram recibido, pero no contenía un mensaje de audio procesable."
        )
        return {"status": "actualización no procesable"}

    except Exception as e:
        logger.error(f"Error al procesar el webhook de Telegram: {e}", exc_info=True)
        # Es importante no devolver un 500 a Telegram si es posible,
        # ya que podría deshabilitar el webhook.
        raise HTTPException(
            status_code=400, detail="Error al procesar la petición"
        ) from e
