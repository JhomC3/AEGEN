# src/core/messaging/message_queue.py
"""
Cola FIFO per-usuario para procesamiento ordenado de mensajes.

Responsabilidad única: gestionar cola de mensajes por usuario
garantizando orden FIFO de procesamiento y respuestas.
"""

import asyncio
import logging
from asyncio import Queue
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Estructura de mensaje en cola."""
    id: str
    user_id: str
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = None
    target_agent: str | None = None

    @classmethod
    def create(cls, user_id: str, content: str, target_agent: str | None = None,
               metadata: dict[str, Any] | None = None) -> "Message":
        """Crea nuevo mensaje con ID único."""
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            target_agent=target_agent
        )


class UserMessageQueue:
    """Cola FIFO por usuario - garantiza orden de respuestas."""

    def __init__(self, user_id: str, max_size: int = 100):
        self.user_id = user_id
        self.messages: Queue[Message] = Queue(maxsize=max_size)
        self.processing = False
        self.current_message: Message | None = None
        self.processed_count = 0
        self.logger = logging.getLogger(__name__)

    async def enqueue_message(self, message: Message) -> bool:
        """
        Agrega mensaje al final de la cola.

        Args:
            message: Mensaje a encolar

        Returns:
            bool: True si se encoló exitosamente
        """
        try:
            if message.user_id != self.user_id:
                self.logger.error(f"Message user_id {message.user_id} doesn't match queue user_id {self.user_id}")
                return False

            # Intentar agregar a cola (no bloqueante)
            self.messages.put_nowait(message)
            self.logger.debug(f"Enqueued message {message.id} for user {self.user_id}")
            return True

        except asyncio.QueueFull:
            self.logger.warning(f"Queue full for user {self.user_id}, dropping message {message.id}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to enqueue message for user {self.user_id}: {e}", exc_info=True)
            return False

    async def get_next_message(self) -> Message | None:
        """
        Obtiene siguiente mensaje en orden FIFO (no bloqueante).

        Returns:
            Optional[Message]: Siguiente mensaje o None si cola vacía
        """
        try:
            message = self.messages.get_nowait()
            self.current_message = message
            self.logger.debug(f"Retrieved message {message.id} for user {self.user_id}")
            return message

        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get next message for user {self.user_id}: {e}", exc_info=True)
            return None

    async def mark_message_processed(self) -> None:
        """Marca mensaje actual como procesado."""
        try:
            if self.current_message:
                self.processed_count += 1
                self.logger.debug(f"Processed message {self.current_message.id} for user {self.user_id}")
                self.current_message = None

        except Exception as e:
            self.logger.error(f"Failed to mark message as processed for user {self.user_id}: {e}", exc_info=True)

    def is_processing(self) -> bool:
        """Verifica si está procesando un mensaje actualmente."""
        return self.processing

    def set_processing(self, processing: bool) -> None:
        """Establece estado de procesamiento."""
        self.processing = processing

    def queue_size(self) -> int:
        """Obtiene tamaño actual de la cola."""
        return self.messages.qsize()

    def is_empty(self) -> bool:
        """Verifica si la cola está vacía."""
        return self.messages.empty()

    def get_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas de la cola."""
        return {
            "user_id": self.user_id,
            "queue_size": self.queue_size(),
            "processing": self.processing,
            "processed_count": self.processed_count,
            "current_message_id": self.current_message.id if self.current_message else None
        }


class MessageQueueManager:
    """Gestor de colas de mensajes por usuario."""

    def __init__(self):
        self.user_queues: dict[str, UserMessageQueue] = {}
        self.logger = logging.getLogger(__name__)

    def get_or_create_queue(self, user_id: str) -> UserMessageQueue:
        """Obtiene o crea cola para usuario."""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = UserMessageQueue(user_id)
            self.logger.debug(f"Created new queue for user {user_id}")
        return self.user_queues[user_id]

    async def enqueue_message(self, user_id: str, content: str,
                            target_agent: str | None = None,
                            metadata: dict[str, Any] | None = None) -> bool:
        """
        Encola mensaje para usuario.

        Args:
            user_id: ID del usuario
            content: Contenido del mensaje
            target_agent: Agente objetivo (opcional)
            metadata: Metadata adicional (opcional)

        Returns:
            bool: True si se encoló exitosamente
        """
        try:
            queue = self.get_or_create_queue(user_id)
            message = Message.create(user_id, content, target_agent, metadata)
            return await queue.enqueue_message(message)

        except Exception as e:
            self.logger.error(f"Failed to enqueue message for user {user_id}: {e}", exc_info=True)
            return False

    def get_queue_stats(self, user_id: str) -> dict[str, Any] | None:
        """Obtiene estadísticas de cola de usuario."""
        queue = self.user_queues.get(user_id)
        return queue.get_stats() if queue else None

    def cleanup_empty_queues(self) -> int:
        """Limpia colas vacías inactivas."""
        empty_queues = [
            user_id for user_id, queue in self.user_queues.items()
            if queue.is_empty() and not queue.is_processing()
        ]

        for user_id in empty_queues:
            del self.user_queues[user_id]

        if empty_queues:
            self.logger.debug(f"Cleaned up {len(empty_queues)} empty queues")

        return len(empty_queues)
