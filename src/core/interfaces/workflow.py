# src/core/interfaces/workflow.py
from abc import ABC, abstractmethod


class IWorkflow(ABC):
    """
    Define la interfaz para un workflow ejecutable.

    Los workflows son las unidades de lógica de negocio que responden a eventos
    publicados en el IEventBus. Cada workflow encapsula un proceso completo.
    """

    @abstractmethod
    async def execute(self, payload: dict) -> None:
        """
        Ejecuta la lógica principal del workflow.

        Este método es invocado por el consumidor del bus de eventos cuando
        llega un nuevo mensaje al topic suscrito.

        Args:
            payload: El diccionario de datos (evento) que dispara el workflow.
        """
        pass
