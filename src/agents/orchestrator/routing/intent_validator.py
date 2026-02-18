from src.core.routing_models import IntentType

from .intent_patterns_data import INTENT_PATTERNS


class IntentValidator:
    """
    Validador de intents basado en palabras clave y patrones.

    Complementa clasificación LLM con patterns específicos
    para aumentar confianza en decisiones claras.
    """

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
        patterns_config = INTENT_PATTERNS.get(intent, [])

        # Soporte para estructura simple (lista) o compleja (dict con positive/negative)
        if isinstance(patterns_config, dict):
            positive_patterns = patterns_config.get("positive_patterns", [])
            negative_patterns = patterns_config.get("negative_patterns", [])

            # Si hay negative patterns y alguno matchea, NO es este intent
            if any(neg in text_lower for neg in negative_patterns):
                return False

            return any(pos in text_lower for pos in positive_patterns)
        # Comportamiento legacy para listas simples
        return any(pattern in text_lower for pattern in patterns_config)
