"""Previews de selección (plantilla, cardio) (fusión SDD 001)."""

from __future__ import annotations

from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.domain_http import (
    _err,
    _get,
    _guardar_pendiente,
    _post,
)


async def _p_plantilla(user_message: str, chat_id: str, fecha: str) -> str:
    import re as _re

    _ = chat_id
    lst = await _get("/api/v1/plantillas")
    e = _err(lst)
    if e:
        return e
    nombres = {x["nombre"].lower(): x for x in lst.get("plantillas", [])}
    m = _re.search(r"plantilla\s+(.+)", user_message.lower())
    cand = (m.group(1).strip() if m else "").removesuffix("hoy").strip()
    match = nombres.get(cand)
    if not match:
        disp = ", ".join(x["nombre"] for x in lst.get("plantillas", []))
        return f"Dime qué plantilla aplico. Disponibles: {disp or 'ninguna'}."
    r = await _post(
        "/api/v1/plantilla/aplicar", {"plantilla_id": match["id"], "fecha": fecha}
    )
    e = _err(r)
    if e:
        return e
    return (
        f"Vista previa de «{match['nombre']}» para el {fecha} (no escribí nada):\n"
        f"{ops.fmt_sets(r.get('sets', []))}\n"
        "Para guardarla, dime «guarda la plantilla» y la confirmamos."
    )


async def _p_cardio(user_message: str, chat_id: str, fecha: str) -> str:
    _ = user_message
    actual = await _get("/api/v1/cardio", {"fecha": fecha})
    e = _err(actual)
    if e:
        return e
    if not actual.get("count"):
        return f"Cardio del {fecha}: no hay sesiones que anotar."
    líneas = [f"• {s.get('hc_id')}: {s.get('titulo')}" for s in actual["sesiones"]]
    canon = {
        "fecha": fecha,
        "hc_ids": sorted(s.get("hc_id", "") for s in actual["sesiones"]),
    }
    h = _guardar_pendiente(chat_id, "cardio_elegir", canon)
    return (
        "Elige la sesión y la anotación (ej.: «anota c1 10,5 km/h») y "
        f"confirma con:\nsí {h}\n" + "\n".join(líneas)
    )
