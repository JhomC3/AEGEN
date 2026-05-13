"""Adaptador para comunicaciones vía WebSocket (Nodos Locales)."""

import logging
from typing import Any

from src.core.interfaces.channel import IChannel
from src.core.schemas.graph import CanonicalEventV1

logger = logging.getLogger(__name__)


class WebSocketChannel(IChannel):
    """
    Implementación del canal WebSocket para el Agentic Hub.
    Permite la conexión de clientes locales y nodos de ejecución.
    """

    def __init__(self, websocket: Any) -> None:
        self._ws = websocket

    @property
    def channel_type(self) -> str:
        return "websocket"

    async def send_response(self, chat_id: str, text: str, **kwargs: Any) -> bool:
        """Envía datos JSON a través del WebSocket."""
        try:
            await self._ws.send_json({
                "type": "response",
                "chat_id": chat_id,
                "content": text,
                **kwargs,
            })
            return True
        except Exception:
            logger.exception("Error enviando mensaje vía WebSocket")
            return False

    async def process_event(self, event: CanonicalEventV1) -> Any:
        """
        Procesa un evento recibido por WS directamente a través del pipeline.
        """
        # TODO: Implementar ruteo directo al MasterOrchestrator
        pass
