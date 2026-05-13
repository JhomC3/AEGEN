"""Servicio para notificar resultados de workers al usuario."""

import logging
from typing import Any

from src.core.interfaces.bus import IEventBus
from src.tools.telegram_interface import telegram_manager

logger = logging.getLogger(__name__)


class WorkerNotificator:
    """
    Escucha eventos de finalización de tareas en el bus y envía
    notificaciones al usuario correspondiente.
    """

    def __init__(self, event_bus: IEventBus) -> None:
        self._bus = event_bus

    async def start(self) -> None:
        """Se suscribe a todos los eventos de finalización de workers."""
        # Suscribirse a un patrón genérico (si el bus lo soporta) o a topics específicos
        # Por ahora usamos un topic base que el WorkerManager publica
        await self._bus.subscribe("worker.done.*", self.handle_worker_result)
        logger.info("WorkerNotificator iniciado y suscrito a resultados.")

    async def handle_worker_result(self, data: dict[str, Any]) -> None:
        """Maneja el resultado de una tarea y lo envía a Telegram."""
        try:
            chat_id = str(data.get("chat_id", ""))
            success = data.get("success", False)
            output = data.get("output", "")
            error = data.get("error")
            skill_id = data.get("skill_id", "agente")

            if not chat_id:
                return

            if success:
                message = f"🔔 *Tarea completada ({skill_id})*\n\n{output}"
            else:
                message = (
                    f"❌ *Error en tarea ({skill_id})*\n\n"
                    f"Lo siento, hubo un problema: {error}"
                )

            # Enviar via Telegram Manager
            await telegram_manager.send_message(chat_id, message)
            logger.info("Notificación de worker enviada a chat %s", chat_id)

        except Exception:
            logger.exception("Error procesando resultado de worker para notificación")
