# src/memory/long_term_memory.py
import json
import logging
from typing import Any

from src.core.engine import llm
from src.memory.redis_buffer import RedisMessageBuffer
from src.memory.services.incremental_extractor import incremental_fact_extraction
from src.memory.services.memory_summarizer import MemorySummarizer

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """
    Gestiona la memoria episódica de largo plazo (Diskless).
    Usa Redis para el buffer caliente y la Google File API para persistencia de largo plazo.
    """

    def __init__(self):
        # Reutilizamos el LLM global configurado en el sistema
        self.llm = llm
        self._buffer_instance = None
        self._summarizer = MemorySummarizer(llm)

        logger.info("LongTermMemoryManager initialized (Diskless Architecture)")

    async def get_buffer(self) -> RedisMessageBuffer:
        """Obtiene la instancia del buffer de Redis (Lazy Initialization)."""
        if self._buffer_instance is None:
            from src.core.dependencies import redis_connection

            if redis_connection is None:
                raise RuntimeError(
                    "Redis connection not available for LongTermMemoryManager"
                )
            self._buffer_instance = RedisMessageBuffer(redis_connection)
        return self._buffer_instance

    async def get_summary(self, chat_id: str) -> dict[str, Any]:
        """Recupera el resumen histórico de Redis y el buffer caliente."""
        buffer = await self.get_buffer()

        # 1. Recuperar resumen de Redis
        from src.core.dependencies import redis_connection

        if redis_connection is None:
            logger.error("Redis no disponible para get_summary")
            return {"summary": "Sin historial previo profesional.", "buffer": []}

        summary_key = f"chat:summary:{chat_id}"
        summary = "Sin historial previo profesional."
        try:
            raw_summary = await redis_connection.get(summary_key)
            if raw_summary:
                if isinstance(raw_summary, bytes):
                    raw_summary = raw_summary.decode("utf-8")
                summary_data = json.loads(raw_summary)
                summary = summary_data.get("summary", summary)
        except Exception as e:
            logger.error(f"Error recuperando resumen de Redis para {chat_id}: {e}")

        # 2. Recuperar buffer de Redis
        raw_buffer = await buffer.get_messages(chat_id)

        return {"summary": summary, "buffer": raw_buffer}

    async def store_raw_message(self, chat_id: str, role: str, content: str):
        """Guarda un mensaje en el búfer de Redis inmediatamente."""
        # Ephemeral mode guard
        try:
            from src.core.profile_manager import user_profile_manager

            profile = await user_profile_manager.load_profile(chat_id)
            if profile.get("memory_settings", {}).get("ephemeral_mode", False):
                logger.debug(
                    f"Ephemeral mode active for {chat_id}, skipping persistence"
                )
                return
        except Exception as e:
            logger.warning(f"Could not check ephemeral mode for {chat_id}: {e}")

        buffer = await self.get_buffer()
        await buffer.push_message(chat_id, role, content)

        # 4.6: Integración con ConsolidationManager
        from src.memory.consolidation_worker import consolidation_manager

        count = await buffer.get_message_count(chat_id)

        # PHASE 2.3: Extracción incremental (cada 5 mensajes)
        if count > 0 and count % 5 == 0:
            logger.info(
                f"Triggering incremental fact extraction for {chat_id} (count: {count})"
            )
            import asyncio

            asyncio.create_task(incremental_fact_extraction(chat_id, buffer))

        if await consolidation_manager.should_consolidate(chat_id, count):
            logger.info(f"Triggering background consolidation for {chat_id}")
            import asyncio

            asyncio.create_task(consolidation_manager.consolidate_session(chat_id))

    async def update_memory(self, chat_id: str):
        """
        Analiza el búfer, actualiza el resumen en Redis y sincroniza con Google Cloud.
        """
        data = await self.get_summary(chat_id)
        current_summary = data["summary"]
        raw_buffer = data["buffer"]

        if not raw_buffer:
            return

        buffer = await self.get_buffer()
        await self._summarizer.update_memory(
            chat_id, current_summary, raw_buffer, buffer
        )


# Instancia singleton
long_term_memory = LongTermMemoryManager()
