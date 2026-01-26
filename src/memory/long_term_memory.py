# src/memory/long_term_memory.py
import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import llm
from src.memory.redis_buffer import RedisMessageBuffer
from src.tools.google_file_search import file_search_tool

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

        logger.info("LongTermMemoryManager initialized (Diskless Architecture)")

        self.summary_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Eres un experto en síntesis de memoria. Tu tarea es actualizar el 'Perfil Histórico' de un usuario basado en nuevos mensajes. "
                "Mantén detalles críticos como nombres, preferencias, hechos importantes y el estado de proyectos actuales. "
                "Sé conciso pero preciso. No borres información antigua a menos que haya sido corregida por el usuario.",
            ),
            (
                "user",
                "PERFIL ACTUAL:\n{current_summary}\n\nNUEVOS MENSAJES:\n{new_messages}\n\nActualiza el perfil integrando los nuevos mensajes:",
            ),
        ])

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
        buffer = await self.get_buffer()
        await buffer.push_message(chat_id, role, content)

        # 4.6: Integración con ConsolidationManager
        from src.memory.consolidation_worker import consolidation_manager

        count = await buffer.get_message_count(chat_id)

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

        # Convertir búfer a texto para el resumen
        new_messages_text = "\n".join([
            f"{m['role']}: {m['content']}" for m in raw_buffer
        ])

        try:
            # Generar nuevo resumen incremental
            chain = self.summary_prompt | self.llm
            response = await chain.ainvoke({
                "current_summary": current_summary,
                "new_messages": new_messages_text,
            })

            new_summary = str(response.content).strip()

            # 1. Persistir resumen en Redis
            from src.core.dependencies import redis_connection

            if redis_connection is None:
                raise RuntimeError("Redis no disponible para update_memory")

            summary_key = f"chat:summary:{chat_id}"
            await redis_connection.set(
                summary_key,
                json.dumps(
                    {"summary": new_summary, "chat_id": chat_id}, ensure_ascii=False
                ),
            )

            # 2. Limpiar el búfer
            buffer = await self.get_buffer()
            await buffer.clear_buffer(chat_id)

            # 3. Sincronizar con Google File Search (Cloud Vault) - Diskless!
            try:
                cloud_content = (
                    f"Historial consolidado del usuario {chat_id}:\n\n{new_summary}"
                )
                await file_search_tool.upload_from_string(
                    content=cloud_content, filename="vault.txt", chat_id=chat_id
                )
                logger.info(f"Bóveda en la nube actualizada (diskless) para {chat_id}")
            except Exception as fe:
                logger.warning(f"No se pudo sincronizar con Google File API: {fe}")

            logger.info(f"Memoria consolidada exitosamente para {chat_id}")

        except Exception as e:
            logger.error(
                f"Error consolidando memoria para {chat_id}: {e}", exc_info=True
            )


# Instancia singleton
long_term_memory = LongTermMemoryManager()
