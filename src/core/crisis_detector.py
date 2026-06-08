# src/core/crisis_detector.py
"""
Deteccion de crisis a nivel de codigo.

Analiza el texto del usuario para detectar senales de crisis
antes de recurrir a guardrails LLM. Usa keywords + heuristica
para evitar falsos positivos por frases metaforicas.
"""

import logging
import re

logger = logging.getLogger(__name__)

_CRISIS_KEYWORDS = re.compile(
    r"\b(suicid|matarme|matar[me]?|morir|muert|acabar[me]?|"
    r"no quiero vivir|no vale la pena|fin de todo|despedida|"
    r"pastillas|sobredosis|cortar[me]?|venas|saltar|tirarme|"
    r"no puedo mas|ya no aguanto|quiero desaparecer)\b",
    re.IGNORECASE,
)

_METAPHOR_CONTEXTS = re.compile(
    r"\b(apagarme|desconectar|morir[me]? de (risa|hambre|sueno|"
    r"calor|frio|aburrimiento)|me muero por|muero por)\b",
    re.IGNORECASE,
)

_EMOTIONAL_INTENSIFIERS = [
    "mucho",
    "demasiado",
    "siempre",
    "nunca",
    "imposible",
    "no puedo",
    "no soporto",
    "no aguanto",
]


def detect_crisis(text: str) -> dict:
    """
    Detecta senales de crisis en el texto del usuario.

    Returns:
        Dict con:
        - is_crisis: bool
        - confidence: float (0.0-1.0)
        - level: str ("none", "low", "medium", "high")
        - keywords_found: list[str]
        - is_metaphor: bool
    """
    if not text or not text.strip():
        return {
            "is_crisis": False,
            "confidence": 0.0,
            "level": "none",
            "keywords_found": [],
            "is_metaphor": False,
        }

    keywords = _CRISIS_KEYWORDS.findall(text)
    metaphors = _METAPHOR_CONTEXTS.findall(text)

    is_metaphor = len(metaphors) > 0 and len(keywords) == 0

    if is_metaphor:
        logger.debug(
            "[CRISIS-DETECTOR] Contexto metaforico detectado, no es crisis real: %s",
            metaphors,
        )
        return {
            "is_crisis": False,
            "confidence": 0.0,
            "level": "none",
            "keywords_found": [],
            "is_metaphor": True,
        }

    if not keywords:
        return {
            "is_crisis": False,
            "confidence": 0.0,
            "level": "none",
            "keywords_found": [],
            "is_metaphor": False,
        }

    text_lower = text.lower()
    intensifier_count = sum(1 for w in _EMOTIONAL_INTENSIFIERS if w in text_lower)

    base_confidence = min(0.5 + (len(keywords) * 0.15), 0.95)
    if intensifier_count > 0:
        base_confidence = min(base_confidence + 0.1, 0.95)

    if base_confidence >= 0.8:
        level = "high"
    elif base_confidence >= 0.5:
        level = "medium"
    else:
        level = "low"

    logger.info(
        "[CRISIS-DETECTOR] Senal de crisis: level=%s, confidence=%.2f, keywords=%s",
        level,
        base_confidence,
        keywords,
    )

    return {
        "is_crisis": level in ("medium", "high"),
        "confidence": base_confidence,
        "level": level,
        "keywords_found": list(set(keywords)),
        "is_metaphor": False,
    }
