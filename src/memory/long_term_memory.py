import json
import logging

from src.core.engine import llm_chat
from src.core.schemas.memory import MemorySummaryV1
from src.memory.redis_buffer import RedisMessageBuffer
from src.memory.services.memory_summarizer import MemorySummarizer

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """Gestiona la memoria episódica de largo plazo."""

    def __init__(self) -> None:
        self.llm = llm_chat
        self._buffer_instance: RedisMessageBuffer | None = None
        self._summarizer = MemorySummarizer(llm_chat)
        logger.info("LongTermMemoryManager initialized (Dual Brain Aware)")

    async def get_buffer(self) -> RedisMessageBuffer:
        """Obtiene la instancia del buffer."""
        if self._buffer_instance is None:
            from src.core.dependencies import redis_connection

            if redis_connection is None:
                raise RuntimeError("Redis not available")
            self._buffer_instance = RedisMessageBuffer(redis_connection)
        return self._buffer_instance

    async def get_summary(self, chat_id: str) -> MemorySummaryV1:
        """Obtiene el resumen actual de Redis garantizando el contrato Pydantic."""
        from src.core.dependencies import redis_connection

        buffer = await self.get_buffer()
        raw_messages = await buffer.get_messages(chat_id)

        if redis_connection:
            key = f"chat:summary:{chat_id}"
            val = await redis_connection.get(key)
            if val:
                if isinstance(val, bytes):
                    val = val.decode("utf-8")

                try:
                    data = json.loads(val)
                    return MemorySummaryV1(
                        summary=data.get("summary", "Perfil activo."),
                        buffer=raw_messages,
                        last_updated=data.get("last_updated"),
                    )
                except Exception:
                    return MemorySummaryV1(summary=val, buffer=raw_messages)

        return MemorySummaryV1(summary="Perfil activo.", buffer=raw_messages)

    async def store_raw_message(self, chat_id: str, role: str, content: str) -> None:
        """Guarda un mensaje en el búfer."""
        try:
            from src.core.profile_manager import user_profile_manager

            profile = await user_profile_manager.load_profile(chat_id)
            if profile.get("memory_settings", {}).get("ephemeral_mode"):
                return
        except Exception as e:
            logger.debug("Profile load error for ephemeral check: %s", e)

        buffer = await self.get_buffer()
        await buffer.push_message(chat_id, role, content)

        count = await buffer.get_message_count(chat_id)
        if count > 0 and count % 5 == 0:
            import asyncio

            from src.memory.services.incremental_extractor import (
                incremental_fact_extraction,
            )

            asyncio.create_task(incremental_fact_extraction(chat_id, buffer))

        from src.memory.consolidation_worker import consolidation_manager

        if await consolidation_manager.should_consolidate(chat_id, count):
            import asyncio

            asyncio.create_task(consolidation_manager.consolidate_session(chat_id))

    async def update_memory(self, chat_id: str) -> None:
        """Actualiza el resumen analizando el buffer."""
        buffer = await self.get_buffer()
        messages = await buffer.get_messages(chat_id)
        if not messages:
            return

        old_data = await self.get_summary(chat_id)
        await self._summarizer.update_memory(
            chat_id, old_data.summary, messages, buffer
        )
        logger.info("Memory summary update triggered for %s", chat_id)


long_term_memory = LongTermMemoryManager()
