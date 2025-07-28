# src/core/interfaces/bus.py
from abc import ABC, abstractmethod
from typing import Awaitable, Callable


class IEventBus(ABC):
    """
    Define la interfaz para un bus de eventos asíncrono.

    Es el núcleo de la comunicación desacoplada en la arquitectura AEGEN Genesis,
    permitiendo que los componentes se comuniquen sin conocerse directamente.
    """

    @abstractmethod
    async def publish(self, topic: str, event: dict) -> None:
        """
        Publica un evento en un topic (canal) específico.

        Args:
            topic: El nombre del canal al que se publica el evento.
            event: El diccionario de datos que representa el evento.
        """
        pass

    @abstractmethod
    async def subscribe(
        self, topic: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Suscribe un manejador (handler) a un topic específico.

        El manejador debe ser una corutina que acepta un diccionario (el evento)
        y no devuelve nada.

        Args:
            topic: El nombre del canal al que se suscribe.
            handler: La función corutina que procesará los eventos de este topic.
        """
        pass
