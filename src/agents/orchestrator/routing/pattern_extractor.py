import re

from src.core.routing_models import EntityInfo


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
