# src/memory/json_sanitizer.py
"""
Utilidad de sanitización JSON resiliente.

Repara errores comunes de formato antes de fallar:
comillas simples, comas finales, y otros artefactos
producidos por serialización incorrecta o LLMs.
"""

import ast
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def safe_json_loads(raw: str | None) -> dict[str, Any] | None:
    """
    Parsea JSON con múltiples estrategias de reparación.

    Intenta: json.loads → regex repair → ast.literal_eval.
    Retorna None solo si todas las estrategias fallan.
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Estrategia 1: JSON estándar
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Estrategia 2: Reparar comillas simples y comas finales
    repaired = _repair_json_string(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Estrategia 3: ast.literal_eval (para dicts de Python)
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    logger.error(
        f"JSON irrecuperable tras 3 estrategias. Primeros 100 chars: {raw[:100]}"
    )
    return None


def _repair_json_string(raw: str) -> str:
    """Aplica reparaciones comunes al string JSON."""
    # Reemplazar comillas simples por dobles (fuera de strings)
    repaired = re.sub(r"(?<![\\])'", '"', raw)
    # Eliminar comas finales antes de } o ]
    return re.sub(r",\s*([}\]])", r"\1", repaired)
