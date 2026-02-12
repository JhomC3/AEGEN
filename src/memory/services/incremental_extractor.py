import asyncio
import logging

from src.memory.fact_extractor import fact_extractor
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.redis_buffer import RedisMessageBuffer

logger = logging.getLogger(__name__)

# ADR-0024: Semáforo global para limitar extracción concurrente (máx 1)
_background_semaphore = asyncio.Semaphore(1)


async def incremental_fact_extraction(chat_id: str, buffer: RedisMessageBuffer) -> None:
    """
    Realiza una extracción de hechos parcial sin limpiar el buffer.
    Protegida por semáforo para evitar saturación de API.
    """
    # Si ya hay una extracción en curso, descartar esta
    if _background_semaphore.locked():
        logger.debug(
            f"Extracción incremental descartada para {chat_id}: "
            f"otra extracción en curso."
        )
        return

    async with _background_semaphore:
        try:
            # 1. Obtener mensajes recientes del buffer
            raw_buffer = await buffer.get_messages(chat_id)

            if not raw_buffer:
                return

            # Usar los últimos 10 mensajes para contexto (en caso de que el buffer sea largo)
            recent_msgs = raw_buffer[-10:]
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}" for m in recent_msgs
            ])

            # 2. Cargar conocimiento actual
            current_knowledge = await knowledge_base_manager.load_knowledge(chat_id)

            # 3. Extraer hechos
            updated_knowledge = await fact_extractor.extract_facts(
                conversation_text, current_knowledge
            )

            # 4. Guardar (y sincronizar a la nube)
            await knowledge_base_manager.save_knowledge(chat_id, updated_knowledge)
            logger.info(f"Incremental fact extraction complete for {chat_id}")

        except Exception as e:
            logger.error(f"Error in incremental fact extraction for {chat_id}: {e}")
