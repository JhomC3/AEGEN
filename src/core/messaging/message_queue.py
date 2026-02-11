# src/core/messaging/message_queue.py
"""
Cola FIFO per-usuario para procesamiento ordenado de mensajes.

Responsabilidad única: gestionar cola de mensajes por usuario
garantizando orden FIFO de procesamiento y respuestas.
"""

import logging
from typing import Any

from src.core.messaging.types import Message
from src.core.messaging.user_queue import UserMessageQueue

logger = logging.getLogger(__name__)


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

    async def enqueue_message(
        self,
        user_id: str,
        content: str,
        target_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
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
            self.logger.error(
                f"Failed to enqueue message for user {user_id}: {e}", exc_info=True
            )
            return False

    def get_queue_stats(self, user_id: str) -> dict[str, Any] | None:
        """Obtiene estadísticas de cola de usuario."""
        queue = self.user_queues.get(user_id)
        return queue.get_stats() if queue else None

    def cleanup_empty_queues(self) -> int:
        """Limpia colas vacías inactivas."""
        empty_queues = [
            user_id
            for user_id, queue in self.user_queues.items()
            if queue.is_empty() and not queue.is_processing()
        ]

        for user_id in empty_queues:
            del self.user_queues[user_id]

        if empty_queues:
            self.logger.debug(f"Cleaned up {len(empty_queues)} empty queues")

        return len(empty_queues)
