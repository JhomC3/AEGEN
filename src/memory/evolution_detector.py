import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class EvolutionDetector:
    """
    Detecta cambios evolutivos en el perfil del usuario usando LLM.
    """

    def __init__(self, llm):
        self.llm = llm
        self.evolution_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un Psicólogo Evolutivo y Analista de Personalidad. Tu objetivo es detectar cambios significativos "
                    "en el perfil del usuario basándote en su última sesión de chat.\n"
                    "Busca:\n"
                    "1. Evolución de vida: Nuevos valores, metas alcanzadas, hitos (milestones).\n"
                    "2. Adaptación de MAGI: ¿Cómo prefiere el usuario que le hablen? (estilo, nivel de humor, formalidad).\n"
                    "3. Preferencias aprendidas: Cosas que le gustan o disgustan específicamente.\n"
                    "\n"
                    "Responde estrictamente en JSON con los campos:\n"
                    "- 'new_values': [lista]\n"
                    "- 'new_goals': [lista]\n"
                    "- 'milestone_detected': 'string' o null\n"
                    "- 'personality_adaptation': {{\n"
                    "    'preferred_style': 'casual'|'formal'|'tecnico'|'empatico',\n"
                    "    'humor_tolerance_delta': float (-0.1 a 0.1),\n"
                    "    'formality_level_delta': float (-0.1 a 0.1),\n"
                    "    'new_preferences': [lista]\n"
                    "}}\n"
                ),
            ),
            (
                "user",
                "PERFIL ACTUAL:\n{current_profile}\n\nRESUMEN DE SESIÓN:\n{session_summary}\n\nDetecta evolución:",
            ),
        ])

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrae un objeto JSON de un bloque de texto usando regex."""
        try:
            # Buscar el primer '{' y el último '}'
            match = re.search(r"(\{[\s\S]*\})", text)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)  # Fallback a loads directo
        except Exception as e:
            logger.error(f"Error extrayendo JSON: {e}")
            raise

    async def detect_evolution(
        self, profile: dict[str, Any], session_summary: str
    ) -> dict[str, Any]:
        """Ejecuta el análisis de evolución."""
        try:
            chain = self.evolution_prompt | self.llm
            response = await chain.ainvoke({
                "current_profile": json.dumps(profile, ensure_ascii=False),
                "session_summary": session_summary,
            })

            return self._extract_json(str(response.content).strip())

        except Exception as e:
            logger.error(f"Error detectando evolución: {e}")
            return {}
