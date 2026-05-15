"""Servicio de notificaciones técnicas para administradores."""

import logging
from typing import Any

from src.core.config import settings
from src.core.interfaces.bus import IEventBus
from src.tools.telegram_interface import telegram_manager

logger = logging.getLogger(__name__)


class AdminNotificator:
    """
    Escucha eventos del sistema y notifica al administrador configurado.
    Responsabilidad única: Alertas críticas fuera de banda.
    """

    def __init__(self, event_bus: IEventBus) -> None:
        self._bus = event_bus
        self._admin_id = settings.ADMIN_CHAT_ID

    async def start(self) -> None:
        """Se suscribe a eventos críticos del sistema."""
        if not self._admin_id:
            logger.warning(
                "ADMIN_CHAT_ID no configurado. Alertas admin deshabilitadas."
            )
            return

        await self._bus.subscribe("system.llm_failure", self.handle_llm_failure)
        logger.info("AdminNotificator iniciado y suscrito a fallos del sistema.")

    async def handle_llm_failure(self, data: dict[str, Any]) -> None:
        """Notifica un fallo de LLM al administrador."""
        try:
            provider = data.get("provider", "Unknown")
            model = data.get("model", "Unknown")
            error = data.get("error", "No details")
            call_type = data.get("call_type", "general")
            corr_id = data.get("correlation_id", "N/A")

            message = (
                f"🚨 *ALERTA TÉCNICA: Fallo de LLM*\n\n"
                f"*Proveedor:* {provider}\n"
                f"*Modelo:* {model}\n"
                f"*Tarea:* {call_type}\n"
                f"*Error:* `{error}`\n\n"
                "El sistema ha intentado un fallback automático. "
                "Revisa los logs si el problema persiste.\n"
                f"_Trace ID: {corr_id}_"
            )

            if self._admin_id:
                await telegram_manager.send_message(self._admin_id, message)
                logger.info("Alerta de sistema enviada al admin %s", self._admin_id)

        except Exception:
            logger.exception("Error enviando alerta al administrador")
