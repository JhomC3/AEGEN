from typing import Any

from fastapi import APIRouter, BackgroundTasks, status

from src.api.adapters.telegram_adapter import process_telegram_update
from src.core import schemas
from src.core.middleware import correlation_id

router = APIRouter()


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
) -> Any:
    """
    Endpoint que actúa como un 'Adaptador de Telegram' con acumulación.
    Delega el procesamiento al adaptador.
    """
    trace_id = correlation_id.get() or "no-trace"
    return await process_telegram_update(request, background_tasks, trace_id)
