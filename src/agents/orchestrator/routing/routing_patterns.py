# src/agents/orchestrator/routing/routing_patterns.py
"""
Pattern matching y validación para routing decisions.

Maneja extracción de entidades con regex patterns y validación
de intents basada en palabras clave específicas.
"""

import re

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.routing_models import EntityInfo, IntentType


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
        IntentType.VULNERABILITY: [
            "cansado",
            "agotado",
            "triste",
            "deprimido",
            "mal",
            "desempleo",
            "problema",
            "solo",
            "ayúdame",
            "siento",
        ],
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
        patterns = self.INTENT_PATTERNS.get(intent, [])

        return any(pattern in text_lower for pattern in patterns)


class SpecialistMapper:
    """
    Mapeador de intents a especialistas disponibles.

    Maneja lógica de mapeo entre clasificación de intents
    y especialistas reales del sistema.
    """

    # Mapeo preferido por intent
    INTENT_TO_SPECIALISTS = {
        IntentType.FILE_ANALYSIS: ["file_handler_agent", "document_processor"],
        IntentType.PLANNING: ["planner_agent", "task_manager"],
        IntentType.SEARCH: ["search_agent", "web_retriever"],
        IntentType.CHAT: ["chat_specialist"],
        IntentType.HELP: ["chat_specialist", "help_agent"],
        IntentType.VULNERABILITY: ["chat_specialist"],
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

        # Fallback seguro siempre disponible
        return "chat_specialist"
