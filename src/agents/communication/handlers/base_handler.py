from abc import ABC, abstractmethod

from agents.communication.dto import GenericMessage


class IMessageHandler(ABC):
    """
    Interfaz abstracta para todos los manejadores de tipos de mensajes.
    Define el contrato que cada manejador debe seguir.
    """

    @abstractmethod
    async def handle(self, message: GenericMessage) -> str:
        """
        Procesa un mensaje genérico y retorna una respuesta textual para el usuario.

        Args:
            message: El objeto de mensaje genérico (DTO) que contiene los datos.

        Returns:
            Un string con la respuesta para enviar al usuario.
        """
        pass
