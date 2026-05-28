import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core import dependencies
from src.core.dependencies import get_sqlite_store
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.redis_buffer import RedisMessageBuffer

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """
    Servicio de sumarización de memoria.
    """

    def __init__(self, llm: Any = None) -> None:
        if llm is None:
            try:
                from src.core.engine import get_rag_llm

                self.llm = get_rag_llm()
            except Exception as e:
                logger.error(f"Error initializing get_rag_llm in MemorySummarizer: {e}")
                self.llm = llm
        else:
            self.llm = llm
        self.summary_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un experto en síntesis de memoria. Tu tarea es "
                    "actualizar el 'Perfil Histórico' de un usuario basado en "
                    "nuevos mensajes. Mantén detalles críticos como nombres, "
                    "preferencias, hechos importantes y el estado de "
                    "proyectos actuales. Sé conciso pero preciso. No borres "
                    "información antigua a menos que haya sido corregida por "
                    "el usuario."
                ),
            ),
            (
                "user",
                (
                    "PERFIL ACTUAL:\n{current_summary}\n\nNUEVOS MENSAJES:\n"
                    "{new_messages}\n\nActualiza el perfil integrando los "
                    "nuevos mensajes:"
                ),
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
        Analiza el búfer (limitando a 10 mensajes seguros para Groq),
        actualiza el resumen y sincroniza.
        """
        # Limitar a 10 mensajes para no exceder los 8k tokens de Groq
        safe_buffer = raw_buffer[-10:]
        new_messages_text = "\n".join([
            f"{m['role']}: {m['content']}" for m in safe_buffer
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
            if dependencies.redis_connection is None:
                raise RuntimeError("Redis no disponible para update_memory")

            summary_key = f"chat:summary:{chat_id}"
            await dependencies.redis_connection.set(
                summary_key,
                json.dumps(
                    {"summary": new_summary, "chat_id": chat_id}, ensure_ascii=False
                ),
            )

            # 2. Limpiar el búfer (independientemente del historial viejo)
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
                    source_skill="consolidation",
                )
                logger.info(f"Summary persisted to SQLite. New chunks: {new_chunks}")
            except Exception as fe:
                logger.warning(f"No se pudo sincronizar con SQLite: {fe}")

            logger.info(f"Memoria consolidada exitosamente para {chat_id}")

        except Exception as e:
            logger.error(
                f"Error consolidando memoria para {chat_id}: {e}", exc_info=True
            )
            # Circuit Breaker: Si falla, vaciamos Redis para evitar bucles
            if len(raw_buffer) > 15:
                logger.warning(
                    "Búfer envenenado con %s mensajes. Purgando.",
                    len(raw_buffer),
                )
                await buffer.clear_buffer(chat_id)
