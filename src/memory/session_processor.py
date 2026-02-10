# src/memory/session_processor.py
"""
Session processor for memory consolidation.

Processes conversational buffers when a session ends or triggers consolidation.
"""

import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import llm
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class SessionProcessor:
    """
    Procesador de sesiones para consolidación de memoria.
    """

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.pipeline = IngestionPipeline(store)
        self.llm = llm

        self.extraction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un experto en extracción de conocimiento. Analiza la siguiente conversación "
                    "y extrae hechos importantes, preferencias del usuario y resúmenes de temas discutidos. "
                    "Formatea la salida como una lista de puntos clave claros y concisos."
                ),
            ),
            ("user", "CONVERSACIÓN:\n{conversation}\n\nExtrae los puntos clave:"),
        ])

    async def process_session(
        self, chat_id: str, messages: List[Dict[str, Any]]
    ) -> int:
        """
        Consolida una sesión de conversación en la memoria de largo plazo.
        """
        if not messages:
            return 0

        # 1. Preparar texto de la conversación
        conv_text = "\n".join([
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        ])

        try:
            # 2. Extraer conocimiento usando LLM
            logger.info(f"Extracting facts for chat {chat_id} using LLM")
            chain = self.extraction_prompt | self.llm
            response = await chain.ainvoke({"conversation": conv_text})
            extracted_points = str(response.content).strip()

            # 3. Ingerir en el pipeline
            # Almacenamos tanto el resumen de la sesión como los puntos extraídos
            new_chunks = await self.pipeline.process_text(
                chat_id=chat_id,
                text=extracted_points,
                memory_type="fact",
                metadata={
                    "source": "session_consolidation",
                    "msg_count": len(messages),
                },
            )

            logger.info(f"Consolidated session for {chat_id}. New chunks: {new_chunks}")
            return new_chunks

        except Exception as e:
            logger.error(f"Error processing session for {chat_id}: {e}", exc_info=True)
            return 0
