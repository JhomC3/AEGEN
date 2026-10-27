"""Previews de escritura del dominio (fusión SDD 001)."""

from __future__ import annotations

from uuid import uuid4

from src.core.config import settings
from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.domain_http import (
    _err,
    _get,
    _guardar_pendiente,
    _pide_confirmacion,
)
from src.personality.skills.bienestar.previews_extra import (
    _p_cardio,
)

# --- Previews de escritura -----------------------------------------------------


async def _p_sesion(user_message: str, chat_id: str, fecha: str) -> str:
    import re as _re

    serie = ops.parse_serie(user_message)
    if not serie:
        return "No entendí la serie. Ejemplo: «guarda Press 80x8 rir1»."
    actual = await _get("/api/v1/sesion", {"fecha": fecha})
    e = _err(actual)
    if e:
        return e
    base = actual.get("sets", [])
    if _re.search(
        r"\b(añadir|añade|añado|agregar|agrega|agrego|sumar|suma|sumo|adicionar|adiciona)\b",
        user_message.lower(),
    ):
        sets = list(base) + [serie]
        modo = f"añadir 1 serie (conserva las {len(base)} existentes)"
    else:
        sets = [serie]
        if base:
            modo = (
                f"REEMPLAZO TOTAL del día (se quitan las {len(base)} series existentes)"
            )
        else:
            modo = "día nuevo"
    canon = {"fecha": fecha, "sets": sets, "base_hash": actual.get("base_hash")}
    h = _guardar_pendiente(chat_id, "sesion_guardar", canon, base)
    return _pide_confirmacion(
        f"Voy a guardar la sesión del {fecha} ({modo}):\n{ops.fmt_sets(sets)}", h
    )


async def _p_diario(user_message: str, chat_id: str, fecha: str) -> str:
    ent = ops.parse_diario(user_message)
    if not ent:
        return "No entendí el alimento. Ejemplo: «registra 50 g de avena»."
    actual = await _get("/api/v1/diario", {"fecha": fecha})
    e = _err(actual)
    if e:
        return e
    base = [
        {"alimento": x.get("alimento"), "cantidad_g": x.get("cantidad_g")}
        for x in actual.get("entradas", [])
    ]
    entradas = list(base) + [ent]
    canon = {
        "fecha": fecha,
        "entradas": entradas,
        "base_hash": actual.get("base_hash"),
    }
    h = _guardar_pendiente(chat_id, "diario_guardar", canon, base)
    return _pide_confirmacion(
        f"Voy a añadir al diario del {fecha} (conserva las {len(base)} "
        f"entradas existentes): {ent['alimento']} {ent['cantidad_g']} g.",
        h,
    )


async def _p_respiracion(user_message: str, chat_id: str, fecha: str) -> str:
    from datetime import datetime

    from zoneinfo import ZoneInfo

    r = ops.parse_respiracion(user_message)
    if not r:
        return "No entendí el patrón. Ejemplo: «registra 4/0/6/0 2 minutos»."
    tz = ZoneInfo(settings.BIENESTAR_TZ or "America/Bogota")
    y, m, d = (int(x) for x in fecha.split("-"))
    ini = int(datetime(y, m, d, 12, 0, tzinfo=tz).timestamp() * 1000)
    fin = ini + int(r["duracion_sec"] * 1000)
    _desfase = datetime(y, m, d, 12, 0, tzinfo=tz).utcoffset()
    desfase = int(_desfase.total_seconds() // 60) if _desfase is not None else 0
    canon = {
        "fecha": fecha,
        "patron": r,
        "uuid": str(uuid4()),
        "start_epoch_ms": ini,
        "end_epoch_ms": fin,
        "desfase_min": desfase,
    }
    h = _guardar_pendiente(chat_id, "respiracion_guardar", canon)
    return _pide_confirmacion(
        f"Voy a registrar respiración del {fecha}: patrón "
        f"{r['inhale_s']}/{r['hold_in_s']}/{r['exhale_s']}/{r['hold_out_s']}, "
        f"{r['duracion_sec']:.0f} s.",
        h,
    )


async def _p_rumbo(user_message: str, chat_id: str, fecha: str) -> str:
    import re as _re

    vals = ops.parse_rumbo_dia(user_message)
    if vals:
        actual = await _get("/api/v1/rumbo/dia", {"fecha": fecha})
        e = _err(actual)
        if e:
            return e
        canon = {"fecha": fecha, **vals, "base_hash": actual.get("base_hash")}
        h = _guardar_pendiente(chat_id, "rumbo_dia", canon, actual.get("dia"))
        return _pide_confirmacion(
            f"Voy a registrar Rumbo del {fecha}: "
            f"{vals['t1']}/{vals['t2']}/{vals['t3']}.",
            h,
        )
    mr = _re.search(
        r"respondo?\s+([a-z0-9]{2,10})\s*:\s*(.+)",
        user_message,
        _re.IGNORECASE | _re.DOTALL,
    )
    if mr:
        actual = await _get(
            "/api/v1/rumbo/respuestas", {"pregunta": mr.group(1).strip().lower()}
        )
        e = _err(actual)
        if e:
            return e
        canon = {
            "pregunta": mr.group(1).strip().lower(),
            "respuesta": mr.group(2).strip(),
        }
        if not canon["respuesta"]:
            return "La respuesta no puede estar vacía."
        h = _guardar_pendiente(
            chat_id, "rumbo_respuesta", canon, (actual.get("vigente") or {}).get("id")
        )
        return _pide_confirmacion(
            f"Voy a responder {canon['pregunta']}: «{canon['respuesta']}».", h
        )
    return (
        "Para Rumbo dime valores t1/t2/t3 (ej.: «rumbo hoy 8 7 9») o "
        "responde con «respondo ex01: …»."
    )


_PREVIEWS = {
    "sesion": _p_sesion,
    "diario": _p_diario,
    "respiracion": _p_respiracion,
    "rumbo": _p_rumbo,
    "cardio": _p_cardio,
}


async def _preview_escritura(user_message: str, dom: str, chat_id: str, tz: str) -> str:
    fecha = ops.resolver_fecha(user_message, tz) or ops.hoy_iso(tz)
    if dom in _PREVIEWS:
        return await _PREVIEWS[dom](user_message, chat_id, fecha)
    return "Esa operación aún no está habilitada por aquí; usa la aplicación directa."
