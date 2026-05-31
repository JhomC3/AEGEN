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
from typing import Any, cast

logger = logging.getLogger(__name__)


def safe_json_loads(raw: str | None) -> dict[str, Any] | None:
    """Parsea JSON con múltiples estrategias de reparación."""
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Estrategia 1: JSON estándar
    try:
        return cast(dict[str, Any], json.loads(raw))
    except json.JSONDecodeError:
        pass

    # Estrategia 2: Reparar comillas simples y comas finales
    repaired = _repair_json_string(raw)
    try:
        return cast(dict[str, Any], json.loads(repaired))
    except json.JSONDecodeError:
        pass

    # Estrategia 3: ast.literal_eval (para dicts de Python)
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return cast(dict[str, Any], result)
    except (ValueError, SyntaxError):
        pass

    # Estrategia 4: Extraer el primer objeto JSON de contenido con
    # múltiples objetos concatenados o texto sobrante
    extracted = _extract_first_json_object(raw)
    if extracted:
        try:
            return cast(dict[str, Any], json.loads(extracted))
        except json.JSONDecodeError:
            pass

    logger.error(
        f"JSON irrecuperable tras 4 estrategias. Primeros 100 chars: {raw[:100]}"
    )
    return None


def _extract_first_json_object(raw: str) -> str | None:
    """Extrae el primer objeto JSON válido de un string con múltiples objetos."""
    brace_count = 0
    start = raw.find("{")
    if start == -1:
        return None
    for i, ch in enumerate(raw[start:], start=start):
        if ch == "{":
            brace_count += 1
        elif ch == "}":
            brace_count -= 1
            if brace_count == 0:
                return raw[start : i + 1]
    return None


def _repair_json_string(raw: str) -> str:
    """Aplica reparaciones comunes al string JSON."""
    # Reemplazar comillas simples por dobles (fuera de strings)
    repaired = re.sub(r"(?<![\\])'", '"', raw)
    # Eliminar comas finales antes de } o ]
    return re.sub(r",\s*([}\]])", r"\1", repaired)
