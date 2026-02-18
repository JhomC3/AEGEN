import asyncio
import logging
from asyncio import Queue
from typing import Any

from src.core.messaging.types import Message


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
        """Agrega mensaje al final de la cola."""
        try:
            if message.user_id != self.user_id:
                self.logger.error(
                    "Message user_id %s mismatch with queue %s",
                    message.user_id,
                    self.user_id,
                )
                return False

            self.messages.put_nowait(message)
            self.logger.debug(
                "Enqueued message %s for user %s", message.id, self.user_id
            )
            return True

        except asyncio.QueueFull:
            self.logger.warning(
                "Queue full for user %s, dropping %s", self.user_id, message.id
            )
            return False
        except Exception as e:
            self.logger.error("Failed to enqueue for user %s: %s", self.user_id, e)
            return False

    async def get_next_message(self) -> Message | None:
        """Obtiene siguiente mensaje."""
        try:
            message = self.messages.get_nowait()
            self.current_message = message
            self.logger.debug(
                "Retrieved message %s for user %s", message.id, self.user_id
            )
            return message
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            self.logger.error("Error get next message: %s", e)
            return None

    async def mark_message_processed(self) -> None:
        """Marca mensaje actual como procesado."""
        try:
            if self.current_message:
                self.processed_count += 1
                self.logger.debug(
                    "Processed message %s for user %s",
                    self.current_message.id,
                    self.user_id,
                )
                self.current_message = None
        except Exception as e:
            self.logger.error("Error mark processed: %s", e)

    def is_processing(self) -> bool:
        return self.processing

    def set_processing(self, processing: bool) -> None:
        self.processing = processing

    def queue_size(self) -> int:
        return self.messages.qsize()

    def is_empty(self) -> bool:
        return self.messages.empty()

    def get_stats(self) -> dict[str, Any]:
        cur_id = self.current_message.id if self.current_message else None
        return {
            "user_id": self.user_id,
            "queue_size": self.queue_size(),
            "processing": self.processing,
            "processed_count": self.processed_count,
            "current_message_id": cur_id,
        }
