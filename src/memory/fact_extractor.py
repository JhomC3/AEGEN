# src/memory/fact_extractor.py
import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import llm

logger = logging.getLogger(__name__)


class FactExtractor:
    """
    Especialista en extracción de hechos estructurados con alta precisión (Clinical Grade).
    Extrae entidades, preferencias, datos médicos y relaciones para la Bóveda de Conocimiento.
    """

    def __init__(self):
        self.llm = llm
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un Analista de Datos Clínicos y experto en Grafos de Conocimiento. "
                    "Tu tarea es extraer hechos atómicos, precisos y verificables de una conversación.\n\n"
                    "REGLAS DE ORO:\n"
                    "1. PRECISIÓN ABSOLUTA: No inventes datos. Si no hay seguridad del 90%+, ignora el hecho.\n"
                    "2. ATOMICIDAD: Cada hecho debe ser una unidad independiente.\n"
                    "3. NO ALUCINACIONES: Si el usuario dice 'mi perro', no asumas que es un Golden Retriever a menos que lo diga.\n"
                    "4. DATOS MÉDICOS: Captura condiciones, medicación, dosis y profesionales con rigor.\n"
                    "5. IDENTIDAD DEL USUARIO: Si el usuario menciona explícitamente su nombre (ej: 'Me llamo X', 'Dime Y'), extráelo.\n\n"
                    "FORMATO DE SALIDA (JSON ESTRICTO):\n"
                    "{{\n"
                    "  'user_name': 'Nombre detectado o null',\n"
                    "  'entities': [{{'name', 'type', 'attributes', 'confidence'}}],\n"
                    "  'preferences': [{{'category', 'value', 'strength'}}],\n"
                    "  'medical': [{{'type', 'name', 'details', 'date'}}],\n"
                    "  'relationships': [{{'person', 'relation', 'attributes'}}],\n"
                    "  'milestones': [{{'description', 'date', 'category'}}]\n"
                    "}}"
                ),
            ),
            (
                "user",
                "CONVERSACIÓN:\n{conversation}\n\nCONOCIMIENTO ACTUAL:\n{current_knowledge}\n\nExtrae y actualiza los hechos:",
            ),
        ])

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrae JSON del texto del LLM."""
        try:
            match = re.search(r"(\{[\s\S]*\})", text)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
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
        """
        Invoca al LLM para extraer nuevos hechos y mezclarlos con el conocimiento actual.
        """
        try:
            chain = self.extraction_prompt | self.llm
            response = await chain.ainvoke({
                "conversation": conversation_text,
                "current_knowledge": json.dumps(current_knowledge, ensure_ascii=False),
            })

            new_knowledge = self._extract_json(str(response.content).strip())
            return self._merge_knowledge(current_knowledge, new_knowledge)

        except Exception as e:
            logger.error(f"Error en FactExtractor: {e}", exc_info=True)
            return current_knowledge

    def _merge_knowledge(
        self, old: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Lógica de mezcla inteligente para evitar duplicados y actualizar atributos.
        """
        merged = old.copy()

        # Merge explícito del nombre de usuario
        # Si el extractor detectó un nombre nuevo (no nulo), ese tiene prioridad absoluta.
        if new.get("user_name"):
            merged["user_name"] = new["user_name"]

        # Simple merge for now, prioritizing new data for attributes
        for key in [
            "entities",
            "preferences",
            "medical",
            "relationships",
            "milestones",
        ]:
            if key not in merged:
                merged[key] = []

            # TODO: Implementar deduplicación por ID o Nombre
            # Por ahora, simplemente añadimos y el LLM se encarga de la coherencia en la siguiente pasada
            # Pero para ser más robustos, podríamos filtrar duplicados exactos
            existing_items = {json.dumps(item, sort_keys=True) for item in merged[key]}
            for item in new.get(key, []):
                item_str = json.dumps(item, sort_keys=True)
                if item_str not in existing_items:
                    merged[key].append(item)

        return merged


# Singleton
fact_extractor = FactExtractor()
