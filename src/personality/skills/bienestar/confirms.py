"""Confirmaciones: ejecutan con precondición atómica del servidor (fusión SDD 001).

Cada escritura envía el `base_hash` obtenido en su preview; el servidor lo
comprueba dentro de la transacción (409 si cambió). Tras éxito se registra la
huella para identificar la acción ante un undo posterior.
"""

from __future__ import annotations

from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.confirms_rumbo import (
    _c_cardio,
    _c_rumbo_dia,
    _c_rumbo_respuesta,
    _c_undo,
)
from src.personality.skills.bienestar.domain_http import (
    _PENDIENTES,
    _ULTIMAS,
    _err,
    _post,
)


def _olvida_si_error(h: str, r: dict) -> str | None:
    """Ante error del servidor el pendiente caduca: devuelve el mensaje."""
    e = _err(r)
    if e:
        _PENDIENTES.pop(h, None)
        if "cambió desde la lectura" in e or "cambió desde" in e:
            return e + " Pide de nuevo la operación para un preview actual."
        return e
    return None


async def _c_sesion(chat_id: str, h: str, pend: dict) -> str:
    canon = pend["canon"]
    r = await _post("/api/v1/sesion", canon)
    msg = _olvida_si_error(h, r)
    if msg:
        return msg
    _PENDIENTES.pop(h, None)
    if r.get("base_hash"):
        _ULTIMAS[(chat_id, "sesion", canon["fecha"])] = r["base_hash"]
    return (
        f"Guardado el {canon['fecha']} ({r.get('saved_count')} series).\n"
        f"{ops.fmt_sets(r.get('sets', []))}\n"
        "Puedes deshacerlo con «deshaz lo último»."
    )


async def _c_diario(chat_id: str, h: str, pend: dict) -> str:
    canon = pend["canon"]
    r = await _post("/api/v1/diario", canon)
    msg = _olvida_si_error(h, r)
    if msg:
        return msg
    _PENDIENTES.pop(h, None)
    if r.get("base_hash"):
        _ULTIMAS[(chat_id, "alimentacion", canon["fecha"])] = r["base_hash"]
    cons = r.get("consumido", {})
    return (
        f"Registrado en el diario del {canon['fecha']}: "
        f"{cons.get('kcal')} kcal en total. "
        "Puedes deshacerlo con «deshaz lo último»."
    )


async def _c_respiracion(chat_id: str, h: str, pend: dict) -> str:
    canon = pend["canon"]
    p = canon["patron"]
    r = await _post(
        "/api/v1/respiracion/sesion",
        {
            "client_session_id": canon["uuid"],
            "start_epoch_ms": canon["start_epoch_ms"],
            "end_epoch_ms": canon["end_epoch_ms"],
            "time_zone_offset_minutes": canon["desfase_min"],
            "patron": {
                "inhale_s": p["inhale_s"],
                "hold_in_s": p["hold_in_s"],
                "exhale_s": p["exhale_s"],
                "hold_out_s": p["hold_out_s"],
            },
        },
    )
    msg = _olvida_si_error(h, r)
    if msg:
        return msg
    _PENDIENTES.pop(h, None)
    dup = " (ya estaba registrada)" if r.get("saved") is False else ""
    return (
        f"Sesión de respiración guardada{dup}: "
        f"{r.get('ciclos_completados')} ciclos el {r.get('fecha')}."
    )


_CONFIRMS = {
    "sesion_guardar": _c_sesion,
    "diario_guardar": _c_diario,
    "respiracion_guardar": _c_respiracion,
    "rumbo_dia": _c_rumbo_dia,
    "rumbo_respuesta": _c_rumbo_respuesta,
    "undo": _c_undo,
}


async def _confirmar(user_message: str, chat_id: str, h: str, tz: str) -> str:
    _ = tz
    pend = _PENDIENTES.get(h)
    if not pend or pend.get("chat") != chat_id:
        return (
            "Ese código no corresponde a un preview vigente. Pide de nuevo "
            "la operación para generar un preview actual."
        )
    op = pend["op"]
    if op == "cardio_elegir":
        return await _c_cardio(chat_id, h, pend, user_message)
    if op in _CONFIRMS:
        return await _CONFIRMS[op](chat_id, h, pend)
    _PENDIENTES.pop(h, None)
    return "Operación desconocida; no se hizo nada."
