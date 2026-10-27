"""Parsing de texto y fechas del subagente de bienestar (fusión SDD 001).

Sin I/O: solo texto y estructuras.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from zoneinfo import ZoneInfo

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_PATRONES_DOMINIO = (
    (
        "rumbo_pregunta",
        (
            r"\b(?:ex|pa|si|ju)\d{2}\b",
            r"\bqué respondí\b",
            r"\bmis respuestas\b",
        ),
    ),
    (
        "alimento",
        (
            r"\bcada 100\b",
            r"\bpor cada 100\b",
            r"\bcuántas calorías\b",
            r"\bqué tiene\b",
        ),
    ),
    (
        "rumbo",
        (
            r"\brumbo\b",
            r"\bmetas?\b",
            r"\bobjetivos?\b",
            r"\bprop[oó]sito\b",
            r"\bpregunta\b",
        ),
    ),
    ("respiracion", (r"\brespira", r"\d+/\d+/\d+/\d+")),
    (
        "cardio",
        (
            r"\bcardio\b",
            r"\bcinta\b",
            r"\bcarrer",
        ),
    ),
    (
        "diario",
        (
            r"\bcom[ií]\b",
            r"\bkcal\b",
            r"\bdieta\b",
            r"\balimento\b",
            r"\bdiario\b",
            r"\bnutri",
        ),
    ),
    (
        "sesion",
        (
            r"\bsesi[oó]n\b",
            r"\bentren",
            r"\bseries?\b",
            r"\brm\b",
            r"\bpress\b",
            r"\bsentadilla\b",
            r"\bpeso\b",
        ),
    ),
    ("sugerencia", (r"\btoca\b", r"\bsugerencia\b", r"\brutina\b")),
    ("plantilla", (r"\bplantilla\b",)),
)


def hoy_iso(tz: str) -> str:
    """Hoy en la zona configurada (formato API)."""
    return datetime.now(ZoneInfo(tz)).date().isoformat()


def resolver_fecha(texto: str, tz: str) -> str | None:
    """Fecha explícita o relativa simple. None = ambigua (pedir aclaración)."""
    t = texto.lower()
    base = datetime.now(ZoneInfo(tz)).date()
    if re.search(r"\bhoy\b", t):
        return base.isoformat()
    if re.search(r"\bayer\b", t):
        return (base - timedelta(days=1)).isoformat()
    if re.search(r"\banteayer\b", t):
        return (base - timedelta(days=2)).isoformat()
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})\s+de\s+([a-zá]+)(?:\s+de\s+(\d{4}))?", t)
    if m and m.group(2) in MESES:
        try:
            return date(
                int(m.group(3) or base.year), MESES[m.group(2)], int(m.group(1))
            ).isoformat()
        except ValueError:
            return None
    if re.search(r"\bmañana\b|\bpasado mañana\b", t):
        return None
    return None


def verbo(texto: str) -> str:
    """consulta | escritura | undo | confirmacion | ambiguo."""
    t = texto.lower()
    if re.search(r"\bdeshaz\b|\bdeshacer\b|\bundo\b", t):
        return "undo"
    if re.search(
        r"\b(guarda|guardar|registra|registrar|anota|anotar|añade|agregar|"
        r"agrega|suma|borra|borrar|elimina|responde|respondo)\b",
        t,
    ):
        return "escritura"
    if re.search(
        r"\b(qu[eé]|cu[aá]nt[oa]s?|c[oó]mo|muestra|muéstrame|dime|historial|"
        r"[uú]ltim|quedan|toca|sugiere|sugerir|lista|estado|tiene|aporta)\b",
        t,
    ):
        return "consulta"
    return "ambiguo"


def dominio(texto: str) -> str | None:
    """Dominio del mensaje o None."""
    t = texto.lower()
    for nombre, patrones in _PATRONES_DOMINIO:
        if any(re.search(p, t) for p in patrones):
            return nombre
    if re.search(r"\d+(?:[.,]\d+)?\s*g\b", t) and re.search(r"\bde\b", t):
        return "diario"
    return None
