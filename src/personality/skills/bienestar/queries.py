"""Consultas de solo lectura del dominio (fusión SDD 001)."""

from __future__ import annotations

from src.personality.skills.bienestar import bienestar_ops as ops
from src.personality.skills.bienestar.domain_http import _err, _get

# --- Consultas (solo lectura) -------------------------------------------------


async def _q_sesion(fecha: str) -> str:
    d = await _get("/api/v1/sesion", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    if not d.get("has_data"):
        return f"Sesión del {fecha}: sin registros."
    return f"Sesión del {fecha}:\n{ops.fmt_sets(d.get('sets', []))}"


async def _q_diario(fecha: str) -> str:
    d = await _get("/api/v1/diario", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    cons = d.get("consumido", {})
    if not d.get("has_data"):
        marca = ""
        if d.get("prefilled"):
            marca = f" (heredado del {d.get('prefill_source')})"
        return f"Diario del {fecha}: sin registros{marca}."
    return (
        f"Diario del {fecha}: {cons.get('kcal')} kcal, "
        f"{cons.get('proteina')} g proteína, {cons.get('carbohidratos')} g carbos, "
        f"{cons.get('grasa')} g grasa."
    )


async def _q_respiracion(fecha: str) -> str:
    d = await _get("/api/v1/respiracion/sesiones", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    if not d.get("count"):
        return f"Respiración del {fecha}: sin sesiones."
    return (
        f"Respiración del {fecha}: {d['count']} sesiones, "
        f"{d.get('minutos_totales')} min, {d.get('ciclos_totales')} ciclos."
    )


async def _q_cardio(fecha: str) -> str:
    d = await _get("/api/v1/cardio", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    if not d.get("count"):
        return f"Cardio del {fecha}: sin sesiones."
    líneas = [
        f"• {s.get('titulo')}: {s.get('duracion_min')} min" for s in d["sesiones"]
    ]
    return f"Cardio del {fecha}:\n" + "\n".join(líneas)


async def _q_rumbo(fecha: str) -> str:
    d = await _get("/api/v1/rumbo/dia", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    dia = d.get("dia") or {}
    sem = d.get("semana", {})
    if dia:
        base = (
            f"Rumbo del {fecha}: día {dia.get('t1', '–')}/"
            f"{dia.get('t2', '–')}/{dia.get('t3', '–')}"
        )
    else:
        base = f"Rumbo del {fecha}: día sin registrar."
    return f"{base} Semana: {sem.get('puntos', '?')}/210."


async def _q_sugerencia(fecha: str) -> str:
    d = await _get("/api/v1/sugerencia", {"fecha": fecha})
    e = _err(d)
    if e:
        return e
    if d.get("tipo") == "rutina":
        return (
            f"Hoy toca rutina ({d.get('explicacion', '')}):\n"
            f"{ops.fmt_sets(d.get('sets', []))}"
        )
    if d.get("tipo") == "descanso":
        return "Hoy toca descanso."
    return "Hoy no hay propuesta (día con datos o sin plan activo)."


async def _q_alimento(user_message: str) -> str:
    d = await _get("/api/v1/alimentos")
    e = _err(d)
    if e:
        return e
    t = user_message.lower()
    cands = [a for a in d.get("alimentos", []) if a["nombre"].lower() in t]
    if not cands:
        return f"No lo encontré en el catálogo ({d.get('count', 0)} alimentos)."
    a = max(cands, key=lambda x: len(x["nombre"]))
    return (
        f"{a['nombre']} (por 100 g): {a.get('kcal')} kcal, "
        f"{a.get('proteina')} g proteína, {a.get('carbohidratos')} g carbos, "
        f"{a.get('grasa')} g grasa."
    )


async def _q_pregunta(user_message: str) -> str:
    import re as _re

    m = _re.search(r"\b((?:ex|pa|si|ju)\d{2})\b", user_message.lower())
    if not m:
        d = await _get("/api/v1/rumbo/preguntas")
        e = _err(d)
        if e:
            return e
        total = sum(len(g.get("preguntas", [])) for g in d.get("preguntas", []))
        return f"Rumbo tiene {total} preguntas con su estado de respuesta."
    pid = m.group(1)
    d = await _get("/api/v1/rumbo/respuestas", {"pregunta": pid})
    e = _err(d)
    if e:
        return e
    vig = d.get("vigente") or {}
    n = len(d.get("historial", []))
    txt = vig.get("respuesta", "—")
    return f"«{pid}» vigente ({vig.get('origen', '?')}): {txt} [{n} en historial]"


_CONSULTAS = {
    "sesion": _q_sesion,
    "diario": _q_diario,
    "respiracion": _q_respiracion,
    "cardio": _q_cardio,
    "rumbo": _q_rumbo,
    "sugerencia": _q_sugerencia,
}


async def _consulta(user_message: str, dom: str, tz: str) -> str:
    if dom == "alimento":
        return await _q_alimento(user_message)
    if dom == "rumbo_pregunta":
        return await _q_pregunta(user_message)
    fecha = ops.resolver_fecha(user_message, tz)
    if fecha is None:
        return "¿Para qué fecha? Puedo usar «hoy», «ayer» o una fecha como 2026-10-04."
    return await _CONSULTAS[dom](fecha)
