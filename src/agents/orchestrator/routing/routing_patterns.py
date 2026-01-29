# src/agents/orchestrator/routing/routing_patterns.py
"""
Pattern matching y validación para routing decisions.

Maneja extracción de entidades con regex patterns y validación
de intents basada en palabras clave específicas.
"""

import logging
import re

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.routing_models import EntityInfo, IntentType

logger = logging.getLogger(__name__)


class PatternExtractor:
    """
    Extractor de entidades basado en patterns complementario a LLM.

    Usa regex patterns para identificar entidades estructuradas
    que el LLM podría pasar por alto.
    """

    def extract_entities_from_text(self, text: str) -> list[EntityInfo]:
        """
        Extrae entidades usando regex patterns robustos.

        Args:
            text: Texto a analizar

        Returns:
            List[EntityInfo]: Lista de entidades encontradas
        """
        entities = []

        # Emails con alta precisión
        entities.extend(self._extract_emails(text))

        # URLs con protocolo
        entities.extend(self._extract_urls(text))

        # Documentos con extensión
        entities.extend(self._extract_documents(text))

        return entities

    def _extract_emails(self, text: str) -> list[EntityInfo]:
        """Extrae direcciones email válidas."""
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        entities = []

        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(
                EntityInfo(
                    type="email",
                    value=match.group(),
                    confidence=0.95,
                    position=match.start(),
                )
            )

        return entities

    def _extract_urls(self, text: str) -> list[EntityInfo]:
        """Extrae URLs con protocolo HTTP/HTTPS."""
        pattern = r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?"
        entities = []

        for match in re.finditer(pattern, text):
            entities.append(
                EntityInfo(
                    type="url",
                    value=match.group(),
                    confidence=0.9,
                    position=match.start(),
                )
            )

        return entities

    def _extract_documents(self, text: str) -> list[EntityInfo]:
        """Extrae nombres de archivos con extensiones comunes."""
        pattern = r"\b\w+\.(pdf|docx?|xlsx?|pptx?|txt|csv|json|xml)\b"
        entities = []

        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(
                EntityInfo(
                    type="document",
                    value=match.group(),
                    confidence=0.85,
                    position=match.start(),
                )
            )

        return entities


class IntentValidator:
    """
    Validador de intents basado en palabras clave y patrones.

    Complementa clasificación LLM con patterns específicos
    para aumentar confianza en decisiones claras.
    """

    # Patrones por intent type
    INTENT_PATTERNS = {
        IntentType.FILE_ANALYSIS: [
            "archivo",
            "documento",
            "pdf",
            "analizar",
            "revisar",
            "examinar",
            "procesar",
            "leer",
            "extraer",
        ],
        IntentType.PLANNING: [
            "planificar",
            "cronograma",
            "organizar",
            "planear",
            "programar",
            "itinerario",
            "agenda",
            "calendario",
        ],
        IntentType.SEARCH: [
            "buscar",
            "encontrar",
            "información sobre",
            "dime sobre",
            "investiga",
            "consulta",
            "averigua",
            "explora",
        ],
        IntentType.HELP: [
            "ayuda",
            "cómo",
            "explicar",
            "tutorial",
            "guía",
            "instrucciones",
            "asistencia",
            "apoyo",
        ],
        IntentType.VULNERABILITY: {
            "positive_patterns": [
                # === 1. Emociones negativas básicas ===
                "miedo",
                "tristeza",
                "ira",
                "asco",
                "ansiedad",
                "angustia",
                # === Emociones secundarias ===
                "soledad",
                "desesperación",
                "culpabilidad",
                "vergüenza",
                "frustración",
                "envidia",
                "agobio",
                "apatía",
                # === 2. Distorsiones cognitivas TCC ===
                "todo o nada",
                "siempre me pasa",
                "nunca logro",
                "fracaso total",
                "todos me",
                "nadie me",
                "nunca funciona",
                "lo peor",
                "terrible",
                "desastre",
                "catástrofe",
                "es mi culpa",
                "por mi culpa",
                "piensan que",
                "me juzgan",
                # === 3. Pensamientos automáticos negativos ===
                "no soy suficiente",
                "no sirvo para",
                "soy un fracaso",
                "nadie me quiere",
                "estoy solo",
                "estoy sola",
                "no lo lograré",
                "no tiene sentido",
                # === 4. Solicitudes de ayuda ===
                "necesito ayuda",
                "ayúdame",
                "no sé qué hacer",
                "necesito desahogarme",
                "quiero hablar",
                # === 5. Síntomas específicos ===
                "muy nervioso",
                "muy nerviosa",
                "estresado",
                "estresada",
                "pánico",
                "sin energía",
                "desmotivado",
                "desmotivada",
                "me siento vacío",
                "me siento vacía",
                "no me valoro",
                "no me acepto",
                # === 6. Triggers contextuales ===
                "cuando me pasa",
                "cada vez que",
                "me ocurre que",
                # === Frases originales mejoradas ===
                "me siento mal",
                "estoy agotado",
                "estoy deprimido",
                "agotado",
                "triste",
                "deprimido",
            ],
            "negative_patterns": [
                # Excluir contextos de trading/técnicos
                "el trade",
                "la operación",
                "el mercado",
                "la bolsa",
                "stop loss",
                "take profit",
                "análisis técnico",
            ],
        },
        IntentType.TOPIC_SHIFT: [
            "deja",
            "basta",
            "para con",
            "otro tema",
            "cambia",
            "olvida",
            "no quiero hablar de",
            "suficiente de",
        ],
    }

    def has_clear_intent_evidence(self, text: str, intent: IntentType) -> bool:
        """
        Verifica si hay evidencia clara del intent en el texto.

        Args:
            text: Texto a evaluar
            intent: Intent a validar

        Returns:
            bool: True si encuentra patterns claros del intent
        """
        text_lower = text.lower()
        patterns_config = self.INTENT_PATTERNS.get(intent, [])

        # Soporte para estructura simple (lista) o compleja (dict con positive/negative)
        if isinstance(patterns_config, dict):
            positive_patterns = patterns_config.get("positive_patterns", [])
            negative_patterns = patterns_config.get("negative_patterns", [])

            # Si hay negative patterns y alguno matchea, NO es este intent
            if any(neg in text_lower for neg in negative_patterns):
                return False

            return any(pos in text_lower for pos in positive_patterns)
        else:
            # Comportamiento legacy para listas simples
            return any(pattern in text_lower for pattern in patterns_config)


class SpecialistMapper:
    """
    Mapeador de intents a especialistas disponibles.

    Maneja lógica de mapeo entre clasificación de intents
    y especialistas reales del sistema.
    """

    # Mapeo preferido por intent
    INTENT_TO_SPECIALISTS = {
        IntentType.FILE_ANALYSIS: ["chat_specialist"],
        IntentType.PLANNING: ["chat_specialist"],
        IntentType.SEARCH: ["chat_specialist"],
        IntentType.CHAT: ["chat_specialist"],
        IntentType.HELP: ["chat_specialist"],
        IntentType.VULNERABILITY: ["cbt_specialist"],
        IntentType.TOPIC_SHIFT: ["chat_specialist"],
    }

    def map_intent_to_specialist(
        self, intent: IntentType, cache: SpecialistCache
    ) -> str:
        """
        Mapea intent a especialista disponible en el sistema.

        Args:
            intent: Intent clasificado
            cache: Cache con especialistas disponibles

        Returns:
            str: Nombre del especialista más apropiado
        """
        available_specialists = list(cache.get_tool_to_specialist_map().values())
        preferred_specialists = self.INTENT_TO_SPECIALISTS.get(
            intent, ["chat_specialist"]
        )

        # Buscar primer especialista disponible en orden de preferencia
        for preferred in preferred_specialists:
            if preferred in available_specialists:
                return preferred
            else:
                # Log cuando preferido no está disponible
                logger.debug(
                    f"Especialista preferido '{preferred}' para intent '{intent.value}' "
                    f"no disponible. Probando siguiente opción."
                )

        logger.warning(
            f"Ningún especialista preferido disponible para intent '{intent.value}'. "
            f"Usando fallback: chat_specialist"
        )
        # Fallback seguro siempre disponible
        return "chat_specialist"
