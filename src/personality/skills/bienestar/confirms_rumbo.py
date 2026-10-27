"""Confirmaciones de Rumbo, cardio y undo (fusión SDD 001).

Rumbo-día usa precondición atómica (`base_hash`, 409). Cardio es upsert por
clave. Undo identifica la acción: si la escritura pasó por esta conversación
compara su huella; si no, lo declara y exige confirmación del kind exacto.
"""

from __future__ import annotations

from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.domain_http import (
    _PENDIENTES,
    _ULTIMAS,
    _err,
    _get,
    _post,
)


async def _c_rumbo_dia(chat_id: str, h: str, pend: dict) -> str:
    canon = pend["canon"]
    r = await _post("/api/v1/rumbo/dia", canon)
    e = _err(r)
    if e:
        _PENDIENTES.pop(h, None)
        if "cambió desde" in e:
            return e + " Pide de nuevo la operación para un preview actual."
        return e
    _PENDIENTES.pop(h, None)
    if r.get("base_hash"):
        _ULTIMAS[(chat_id, "rumbo", canon["fecha"])] = r["base_hash"]
    return (
        f"Rumbo del {canon['fecha']}: {r.get('score')}/30. "
        "Puedes deshacerlo con «deshaz lo último»."
    )


async def _c_rumbo_respuesta(chat_id: str, h: str, pend: dict) -> str:
    _ = chat_id
    canon = pend["canon"]
    r = await _post("/api/v1/rumbo/respuesta", canon)
    e = _err(r)
    if e:
        _PENDIENTES.pop(h, None)
        return e
    _PENDIENTES.pop(h, None)
    return (
        f"Respuesta guardada para {canon['pregunta']}. "
        "Puedes deshacerla con «deshaz lo último»."
    )


async def _c_cardio(chat_id: str, h: str, pend: dict, user_message: str) -> str:
    import re as _re

    _ = chat_id
    hc = _re.search(r"\b([A-Za-z0-9_:-]{2,40})\b", user_message)
    hc_id = hc.group(1) if hc else ""
    if hc_id not in pend["canon"].get("hc_ids", []):
        return (
            "Dime el id exacto de la sesión (los listados arriba) "
            "junto al código de confirmación."
        )
    resto = user_message.split(hc_id, 1)[1] if hc_id in user_message else ""
    r = await _post(
        "/api/v1/cardio/anotacion", {"hc_id": hc_id, "velocidad_kmh": ops.num(resto)}
    )
    e = _err(r)
    if e:
        _PENDIENTES.pop(h, None)
        return e
    _PENDIENTES.pop(h, None)
    return f"Anotación guardada para {hc_id}."


def _huella_actual(kind: object, fecha: object) -> tuple[str | None, str | None]:
    """Recurso para verificar la cima de la pila (ruta GET, fecha)."""
    if kind == "sesion" and isinstance(fecha, str) and fecha:
        return ("/api/v1/sesion", fecha)
    if kind == "alimentacion" and isinstance(fecha, str) and fecha:
        return ("/api/v1/diario", fecha)
    return (None, None)


async def _c_undo(chat_id: str, h: str, pend: dict) -> str:
    peek = await _get("/api/v1/undo/peek")
    e = _err(peek)
    if e:
        _PENDIENTES.pop(h, None)
        return e
    want = pend["canon"].get("expected", {})
    if peek.get("entry_id") != want.get("id") or peek.get("kind") != want.get("kind"):
        _PENDIENTES.pop(h, None)
        return (
            "La pila de undo cambió desde el preview; no deshice nada. "
            "Pide «deshaz lo último» de nuevo."
        )
    kind, fecha = peek.get("kind"), peek.get("fecha_iso", "")
    ruta, _ = _huella_actual(kind, fecha)
    preciso = False
    if ruta and (chat_id, kind, fecha or "") in _ULTIMAS:
        actual = await _get(ruta, {"fecha": fecha})
        if _err(actual) is not None:
            _PENDIENTES.pop(h, None)
            return (
                "No pude comprobar el estado actual; no deshice nada. "
                "Revisa el día en la aplicación directa."
            )
        if actual.get("base_hash") != _ULTIMAS[(chat_id, kind, fecha or "")]:
            _PENDIENTES.pop(h, None)
            return (
                "Algo escribió después de tu última acción; deshacer ahora "
                "revertiría un cambio ajeno. Revisa el día en la aplicación "
                "directa antes de decidir."
            )
        preciso = True
    r = await _post("/api/v1/undo", {"expected": {"id": want["id"], "kind": kind}})
    e = _err(r)
    if e:
        _PENDIENTES.pop(h, None)
        return e
    _PENDIENTES.pop(h, None)
    _ULTIMAS.pop((chat_id, kind, fecha or ""), None)
    if preciso:
        return (
            f"Deshecho ({r.get('kind')}). Era tu última escritura de esta conversación."
        )
    return (
        f"Deshecho ({r.get('kind')}). Era la acción confirmada en el preview "
        "(no verifiqué que fuera una escritura de esta conversación)."
    )
