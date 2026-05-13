"""Interfaz para canales de comunicación (Gateway Protocol)."""

from abc import ABC, abstractmethod
from typing import Any

from src.core.schemas.graph import CanonicalEventV1


class IChannel(ABC):
    """
    Define el contrato para un canal que recibe eventos y envía respuestas.
    """

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Nombre del canal (ej: 'telegram', 'websocket')."""
        pass

    @abstractmethod
    async def send_response(self, chat_id: str, text: str, **kwargs: Any) -> bool:
        """Envía una respuesta al usuario a través del canal."""
        pass

    @abstractmethod
    async def process_event(self, event: CanonicalEventV1) -> Any:
        """Procesa un evento canónico a través del pipeline del orquestador."""
        pass
