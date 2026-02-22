# src/memory/fact_extractor.py
import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import llm
from src.memory.fact_utils import merge_fact_knowledge

logger = logging.getLogger(__name__)


class FactExtractor:
    """
    Especialista en extracción de hechos estructurados con alta precisión.
    """

    def __init__(self) -> None:
        self.llm = llm
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un extractor de hechos estructurados. Tu tarea es "
                    "identificar datos atómicos de una conversación y "
                    "clasificarlos por origen y sensibilidad.\n\n"
                    "REGLAS:\n"
                    "1. SOLO extrae hechos EXPLÍCITOS: datos que el usuario "
                    "dijo literalmente.\n"
                    "2. NO INFERIR: Si el usuario no lo dijo con sus palabras, "
                    "NO lo extraigas.\n"
                    "3. source_type SIEMPRE debe ser 'explicit'.\n"
                    "4. CONFIANZA: Solo incluye hechos con confidence >= 0.8.\n"
                    "5. EVIDENCIA: Incluye la cita textual EXACTA.\n"
                    "6. SENSIBILIDAD: 'low', 'medium', 'high'.\n"
                    "7. NO DIAGNOSTIQUES.\n"
                    "8. PRECISIÓN: Sin cita textual, NO lo incluyas.\n"
                    "9. Extrae el nombre en 'user_name'.\n\n"
                    "FORMATO (JSON ESTRICTO):\n"
                    "{{\n"
                    '  "user_name": "nombre o null",\n'
                    '  "entities": [{{"name", "type", "attributes", '
                    '"source_type", "confidence", "evidence", '
                    '"sensitivity"}}],\n'
                    '  "preferences": [{{"category", "value", "strength", '
                    '"source_type", "confidence", "evidence", '
                    '"sensitivity"}}],\n'
                    '  "medical": [{{"type", "name", "details", "date", '
                    '"source_type", "confidence", "evidence", '
                    '"sensitivity"}}],\n'
                    '  "relationships": [{{"person", "relation", '
                    '"attributes", "source_type", "confidence", '
                    '"evidence", "sensitivity"}}],\n'
                    '  "milestones": [{{"description", "date", "category", '
                    '"source_type", "confidence", "evidence", '
                    '"sensitivity"}}]\n'
                    "}}"
                ),
            ),
            (
                "user",
                (
                    "CONVERSACIÓN:\n{conversation}\n\nCONOCIMIENTO ACTUAL:\n"
                    "{current_knowledge}\n\nExtrae y actualiza los hechos:"
                ),
            ),
        ])

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrae JSON del texto del LLM."""
        try:
            match = re.search(r"(\{[\s\S]*\})", text)
            data = json.loads(match.group(1)) if match else json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Error parseando JSON de FactExtractor: {e}")
            return {
                "user_name": None,
                "entities": [],
                "preferences": [],
                "medical": [],
                "relationships": [],
                "milestones": [],
            }

    async def extract_facts(
        self, conversation_text: str, current_knowledge: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoca al LLM para extraer y mezclar hechos."""
        try:
            chain = self.extraction_prompt | self.llm
            response = await chain.ainvoke({
                "conversation": conversation_text,
                "current_knowledge": json.dumps(current_knowledge, ensure_ascii=False),
            })

            new_knowledge = self._extract_json(str(response.content).strip())
            return merge_fact_knowledge(current_knowledge, new_knowledge)

        except Exception as e:
            logger.error(f"Error en FactExtractor: {e}", exc_info=True)
            return current_knowledge


# Singleton
fact_extractor = FactExtractor()


# Singleton
fact_extractor = FactExtractor()
