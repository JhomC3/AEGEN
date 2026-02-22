import asyncio
import contextlib
import logging
from uuid import uuid4

from src.api.services.event_processor import event_processor
from src.core.messaging.outbox import outbox_manager
from src.core.schemas.graph import CanonicalEventV1

logger = logging.getLogger(__name__)


class ProactiveWorker:
    """Worker que evalúa la bandeja de salida y despacha mensajes proactivos."""

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"ProactiveWorker iniciado (intervalo: {self.interval_seconds}s)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("ProactiveWorker detenido")

    async def _loop(self) -> None:
        while self._running:
            try:
                messages = await outbox_manager.get_pending_messages()
                for msg in messages:
                    await self._dispatch(msg)
            except Exception as e:
                logger.error(f"Error en ProactiveWorker: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _dispatch(self, msg_record: dict) -> None:
        chat_id = msg_record["chat_id"]
        intent = msg_record["intent"]
        msg_id = msg_record["id"]

        logger.info(f"Despachando mensaje proactivo a {chat_id}: {intent}")

        event = CanonicalEventV1(
            event_id=uuid4(),
            event_type="text",
            source="proactive_system",
            chat_id=chat_id,
            user_id=chat_id,
            content=f"[SYSTEM_PROACTIVE_PROMPT] {intent}",
            metadata={"is_proactive": True},
        )

        try:
            # Recreamos un procesador para este evento
            # En producción se podría inyectar
            processor = event_processor
            await processor.process_event(event)
            await outbox_manager.mark_as_sent(msg_id)
        except Exception as e:
            logger.error(f"Error procesando mensaje proactivo {msg_id}: {e}")


proactive_worker = ProactiveWorker()
