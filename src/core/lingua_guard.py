import logging
import re

from src.core.engine import llm_core

logger = logging.getLogger(__name__)

# Lista negra de regionalismos no deseados (Reglas de Escudo de Neutralidad)
BANNED_PATTERNS = [
    (r"\bvos\b", "tú"),
    (r"\btenés\b", "tienes"),
    (r"\bpodés\b", "puedes"),
    (r"\bsabés\b", "sabes"),
    (r"\bhacés\b", "haces"),
    (r"\btío\b", "amigo"),
    (r"\bchaval\b", "amigo"),
    (r"\bvale\b", "ok"),
]


class LinguaGuard:
    """
    Servicio de blindaje lingüístico para asegurar la neutralidad del asistente.
    Actúa como un filtro de salida antes de enviar mensajes al usuario.
    """

    def __init__(self) -> None:
        self.enabled = True

    async def protect(self, text: str) -> str:
        """
        Escanea y corrige regionalismos.
        Si detecta infracciones, intenta una corrección determinista.
        Si la infracción es compleja, usa llm_core para neutralizar.
        """
        if not text:
            return text

        # 1. Detección rápida por Regex
        has_issue = False
        for pattern, _ in BANNED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                has_issue = True
                break

        if not has_issue:
            return text

        logger.info("Detectado regionalismo. Iniciando neutralización...")

        # 2. Corrección por LLM Core (más segura que regex para mantener fluidez)
        try:
            # Prompt ultra-corto y técnico para el motor de 120B
            prompt = (
                "Editor neutro. Reescribe el mensaje "
                "sin regionalismos (tío, vos, tenés). "
                "Usa tuteo neutro. Mantén el sentido.\n\n"
                f"Mensaje original: {text}\n\n"
                "Mensaje neutralizado:"
            )

            response = await llm_core.ainvoke(prompt)
            neutralized_text = str(response.content).strip()

            if neutralized_text:
                logger.info("LinguaGuard: Texto neutralizado exitosamente.")
                return neutralized_text
        except Exception as e:
            logger.error(f"LinguaGuard: Error en corrección por LLM: {e}")

        # 3. Fallback a Regex si el LLM falla
        corrected_text = text
        for pattern, replacement in BANNED_PATTERNS:
            corrected_text = re.sub(
                pattern, replacement, corrected_text, flags=re.IGNORECASE
            )

        return corrected_text


lingua_guard = LinguaGuard()
