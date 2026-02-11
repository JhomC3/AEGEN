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
                    "Eres un extractor de hechos estructurados. Tu tarea es identificar "
                    "datos atómicos de una conversación y clasificarlos por origen y sensibilidad.\n\n"
                    "REGLAS:\n"
                    "1. CLASIFICA cada hecho como 'explicit' (el usuario lo dijo literalmente) o "
                    "'inferred' (es tu interpretación del texto).\n"
                    "2. CONFIANZA: Para hechos 'explicit', confidence=1.0. Para 'inferred', asigna 0.5-0.9.\n"
                    "3. EVIDENCIA: Incluye la cita textual exacta del usuario que soporta el hecho.\n"
                    "4. SENSIBILIDAD: 'low' (gustos, datos demográficos), 'medium' (relaciones, trabajo), "
                    "'high' (salud mental, médico, trauma, emociones fuertes).\n"
                    "5. NO DIAGNOSTIQUES. No afirmes rasgos estables. Si detectas un posible patrón "
                    "cognitivo, etiquétalo como hipótesis inferred con evidencia.\n"
                    "6. PRECISIÓN: Si no hay seguridad del 90%+, ignora el hecho.\n"
                    "7. Si el usuario menciona su nombre, extráelo en 'user_name'.\n\n"
                    "FORMATO (JSON ESTRICTO):\n"
                    "{{\n"
                    '  "user_name": "nombre o null",\n'
                    '  "entities": [{{"name", "type", "attributes", "source_type", '
                    '"confidence", "evidence", "sensitivity"}}],\n'
                    '  "preferences": [{{"category", "value", "strength", "source_type", '
                    '"confidence", "evidence", "sensitivity"}}],\n'
                    '  "medical": [{{"type", "name", "details", "date", "source_type", '
                    '"confidence", "evidence", "sensitivity"}}],\n'
                    '  "relationships": [{{"person", "relation", "attributes", "source_type", '
                    '"confidence", "evidence", "sensitivity"}}],\n'
                    '  "milestones": [{{"description", "date", "category", "source_type", '
                    '"confidence", "evidence", "sensitivity"}}]\n'
                    "}}"
                ),
            ),
            (
                "user",
                "CONVERSACIÓN:\n{conversation}\n\nCONOCIMIENTO ACTUAL:\n{current_knowledge}\n\n"
                "Extrae y actualiza los hechos:",
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

    @staticmethod
    def _identity_key(item: dict[str, Any], category: str) -> str:
        """Returns a dedup key based on the semantic identity of a fact."""
        if category == "entities":
            return f"{item.get('name', '')}::{item.get('type', '')}".lower()
        if category == "relationships":
            return f"{item.get('person', '')}::{item.get('relation', '')}".lower()
        if category == "medical":
            return f"{item.get('name', '')}::{item.get('type', '')}".lower()
        if category == "preferences":
            return f"{item.get('category', '')}::{item.get('value', '')}".lower()
        if category == "milestones":
            return f"{item.get('description', '')}".lower()
        return json.dumps(item, sort_keys=True)

    def _merge_knowledge(
        self, old: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merges new knowledge into old, deduplicating by semantic identity.
        New items with the same identity key update the old item's attributes.
        """
        merged = old.copy()

        # Merge explícito del nombre de usuario
        if new.get("user_name"):
            merged["user_name"] = new["user_name"]

        for key in (
            "entities",
            "preferences",
            "medical",
            "relationships",
            "milestones",
        ):
            self._merge_category(merged, new, key)

        return merged

    def _merge_category(
        self, merged: dict[str, Any], new: dict[str, Any], key: str
    ) -> None:
        """Helper to merge a specific category of facts."""
        if key not in merged:
            merged[key] = []

        # Index existing items by identity key
        existing: dict[str, int] = {
            self._identity_key(item, key): idx for idx, item in enumerate(merged[key])
        }

        for item in new.get(key, []):
            ik = self._identity_key(item, key)
            if ik in existing:
                # Update existing item (merge attributes, keep higher confidence)
                old_item = merged[key][existing[ik]]
                if isinstance(old_item.get("attributes"), dict) and isinstance(
                    item.get("attributes"), dict
                ):
                    old_item["attributes"].update(item["attributes"])

                # Overwrite with new data if same/higher confidence
                if item.get("confidence", 0) >= old_item.get("confidence", 0):
                    for field in (
                        "source_type",
                        "confidence",
                        "evidence",
                        "sensitivity",
                    ):
                        if field in item:
                            old_item[field] = item[field]
            else:
                merged[key].append(item)
                existing[ik] = len(merged[key]) - 1


# Singleton
fact_extractor = FactExtractor()
