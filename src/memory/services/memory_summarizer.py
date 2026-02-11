import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from src.core.dependencies import get_sqlite_store, redis_connection
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.redis_buffer import RedisMessageBuffer

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """
    Servicio de sumarización de memoria.
    """

    def __init__(self, llm):
        self.llm = llm
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

    async def update_memory(
        self,
        chat_id: str,
        current_summary: str,
        raw_buffer: list[dict],
        buffer: RedisMessageBuffer,
    ) -> None:
        """
        Analiza el búfer, actualiza el resumen en Redis y sincroniza con SQLite.
        """
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
            await buffer.clear_buffer(chat_id)

            # 3. Sincronizar con SQLite (Nueva Memoria Local-First)
            try:
                store = get_sqlite_store()
                pipeline = IngestionPipeline(store)

                new_chunks = await pipeline.process_text(
                    chat_id=chat_id,
                    text=new_summary,
                    memory_type="conversation",
                    metadata={"source": "long_term_memory_summary"},
                )
                logger.info(f"Summary persisted to SQLite. New chunks: {new_chunks}")
            except Exception as fe:
                logger.warning(f"No se pudo sincronizar con SQLite: {fe}")

            logger.info(f"Memoria consolidada exitosamente para {chat_id}")

        except Exception as e:
            logger.error(
                f"Error consolidando memoria para {chat_id}: {e}", exc_info=True
            )
