"""Utilidades de hash, confirmación y formato (fusión SDD 001)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from zoneinfo import ZoneInfo

from src.personality.skills.bienestar.entry_parse import (
    num as num,
)
from src.personality.skills.bienestar.entry_parse import (
    parse_diario as parse_diario,
)
from src.personality.skills.bienestar.entry_parse import (
    parse_respiracion as parse_respiracion,
)
from src.personality.skills.bienestar.entry_parse import (
    parse_rumbo_dia as parse_rumbo_dia,
)
from src.personality.skills.bienestar.entry_parse import (
    parse_serie as parse_serie,
)
from src.personality.skills.bienestar.text_parse import (
    dominio as dominio,
)
from src.personality.skills.bienestar.text_parse import (
    resolver_fecha as resolver_fecha,
)
from src.personality.skills.bienestar.text_parse import (
    verbo as verbo,
)


def hoy_iso(tz: str) -> str:
    """Hoy en la zona configurada (formato API)."""
    return datetime.now(ZoneInfo(tz)).date().isoformat()


def hash_preview(chat_id: str, operacion: str, canonico: dict) -> str:
    """Hash de 12 hex que vincula chat + operación + datos del preview."""
    raw = json.dumps(
        {"chat": chat_id, "op": operacion, "d": canonico},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def extraer_hash_confirmacion(texto: str) -> str | None:
    """Hash de confirmación si el mensaje confirma explícitamente."""
    if not re.search(
        r"\b(s[ií]|confirmo|confirma|confirmar|dale|hazlo|adelante)\b", texto.lower()
    ):
        return None
    m = re.search(r"\b([0-9a-f]{12})\b", texto.lower())
    return m.group(1) if m else None


def fmt_sets(sets: list) -> str:
    """«Press Prueba: 80 kg × 8 (RIR 1, RM 104)» por serie."""
    lineas = []
    for s in sets:
        base = f"{s.get('ejercicio', '?')}: {s.get('kg')} kg × {s.get('reps')}"
        if s.get("rir") is not None:
            base += f" (RIR {s['rir']}"
            base += f", RM {s['rm']})" if s.get("rm") is not None else ")"
        elif s.get("rm") is not None:
            base += f" (RM {s['rm']})"
        lineas.append(base)
    return "\n".join(f"• {línea}" for línea in lineas)
