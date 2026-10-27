"""Dominio de Rumbo simple: identidad, día 1–10 y scores derivados.

Validación en el borde; `src/database.py` (vía `db_rumbo_simple`) es la única
capa con SQL. Score siempre derivado, nunca persistido.
"""

from datetime import date, timedelta

from src.database import (
    get_respuesta_historial,
    get_respuesta_vigente,
    get_rumbo_dias_rango,
    get_rumbo_yo,
)
from src.database import (
    guardar_respuesta as _guardar_respuesta_db,
)
from src.database import (
    save_rumbo_dia as _save_dia,
)
from src.database import (
    save_rumbo_yo as _save_yo,
)
from src.models import RumboDiaInput, RumboYoInput, ValidationError

__all__ = [
    "guardar_dia",
    "guardar_respuesta",
    "guardar_yo",
    "historial_pregunta",
    "parse_fecha",
    "preguntas_con_estado",
    "score_dia",
    "score_semana",
    "serie_anual_52",
    "vigente_pregunta",
]

_MAX_TEXTO = 500
_MAX_NOMBRE = 100
_MAX_RESPUESTA = 2000


def parse_fecha(fecha: str) -> str:
    texto = str(fecha or "").strip()
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise ValidationError("Fecha inválida.") from None


def _texto(valor: str, max_len: int) -> str:
    t = str(valor or "").strip()
    if len(t) > max_len:
        raise ValidationError(f"Texto demasiado largo (máx. {max_len}).")
    return t


def _nivel(valor: int | str) -> int:
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise ValidationError("El valor debe ser un número del 1 al 10.") from None
    if not 1 <= n <= 10:
        raise ValidationError("El valor debe ser un número del 1 al 10.")
    return n


def guardar_yo(db_path: str, data: RumboYoInput) -> dict:
    yo = {
        "quien_soy": _texto(data.quien_soy, _MAX_TEXTO),
        "quien_no": _texto(data.quien_no, _MAX_TEXTO),
        "construyendo": _texto(data.construyendo, _MAX_TEXTO),
        "t1_nombre": _texto(data.t1_nombre, _MAX_NOMBRE) or "Tarea 1",
        "t2_nombre": _texto(data.t2_nombre, _MAX_NOMBRE) or "Tarea 2",
        "t3_nombre": _texto(data.t3_nombre, _MAX_NOMBRE) or "Tarea 3",
    }
    _save_yo(db_path, **yo)
    return get_rumbo_yo(db_path)


def guardar_dia(db_path: str, data: RumboDiaInput, base_hash: str | None = None, conn=None) -> dict:
    fecha_iso = parse_fecha(data.fecha)
    t1, t2, t3 = _nivel(data.t1), _nivel(data.t2), _nivel(data.t3)
    _save_dia(db_path, fecha_iso, t1, t2, t3, base_hash=base_hash, conn=conn)
    return {"fecha": fecha_iso, "t1": t1, "t2": t2, "t3": t3, "score": score_dia(t1, t2, t3)}


def score_dia(t1: int, t2: int, t3: int) -> int:
    return int(t1) + int(t2) + int(t3)


def _lunes(fecha_iso: str) -> date:
    d = date.fromisoformat(fecha_iso)
    return d - timedelta(days=d.weekday())


def score_semana(db_path: str, fecha: str) -> dict:
    """Semana lunes–domingo de `fecha`: puntos, máx 210 y detalle por día."""
    fecha_iso = parse_fecha(fecha)
    lunes = _lunes(fecha_iso)
    domingo = lunes + timedelta(days=6)
    rows = {
        r["fecha"]: r for r in get_rumbo_dias_rango(db_path, lunes.isoformat(), domingo.isoformat())
    }
    dias = []
    puntos = 0
    for i in range(7):
        iso = (lunes + timedelta(days=i)).isoformat()
        r = rows.get(iso)
        p = score_dia(r["t1"], r["t2"], r["t3"]) if r else 0
        puntos += p
        dias.append({"fecha": iso, "puntos": p})
    return {
        "lunes": lunes.isoformat(),
        "domingo": domingo.isoformat(),
        "puntos": puntos,
        "max": 210,
        "dias": dias,
    }


def serie_anual_52(db_path: str, fecha: str) -> list[dict]:
    """Trailing 52 semanas (la última es la semana de `fecha`): puntos por semana."""
    fecha_iso = parse_fecha(fecha)
    lunes_actual = _lunes(fecha_iso)
    inicio = lunes_actual - timedelta(weeks=51)
    fin = lunes_actual + timedelta(days=6)
    rows = {
        r["fecha"]: r for r in get_rumbo_dias_rango(db_path, inicio.isoformat(), fin.isoformat())
    }
    serie = []
    for w in range(52):
        lunes = inicio + timedelta(weeks=w)
        puntos = 0
        for i in range(7):
            r = rows.get((lunes + timedelta(days=i)).isoformat())
            if r:
                puntos += score_dia(r["t1"], r["t2"], r["t3"])
        serie.append({"semana": lunes.isoformat(), "puntos": puntos})
    return serie


def _pregunta_valida(pregunta_id: str) -> dict:
    from src.rumbo_preguntas import POR_ID

    pid = str(pregunta_id or "").strip()
    pregunta = POR_ID.get(pid)
    if pregunta is None:
        raise ValidationError("Pregunta desconocida.")
    return pregunta


def guardar_respuesta(db_path: str, pregunta_id: str, respuesta: str, conn=None) -> dict:
    pregunta = _pregunta_valida(pregunta_id)
    texto = _texto(respuesta, _MAX_RESPUESTA)
    if not texto:
        raise ValidationError("La respuesta no puede estar vacía.")
    rid = _guardar_respuesta_db(db_path, pregunta["id"], texto, conn=conn)
    return {"id": rid, "pregunta": pregunta["id"], "respuesta": texto}


def vigente_pregunta(db_path: str, pregunta_id: str) -> dict | None:
    _pregunta_valida(pregunta_id)
    return get_respuesta_vigente(db_path, str(pregunta_id).strip())


def historial_pregunta(db_path: str, pregunta_id: str) -> list[dict]:
    _pregunta_valida(pregunta_id)
    return get_respuesta_historial(db_path, str(pregunta_id).strip())


def preguntas_con_estado(db_path: str) -> list[dict]:
    """Catálogo con vigente (texto corto) y flag de respondida, por grupo."""
    from src.rumbo_preguntas import GRUPOS, PREGUNTAS

    por_grupo: dict[str, list[dict]] = {g: [] for g in GRUPOS}
    for p in PREGUNTAS:
        vigente = get_respuesta_vigente(db_path, p["id"])
        por_grupo[p["grupo"]].append(
            {
                "id": p["id"],
                "grupo": p["grupo"],
                "corta": p["corta"],
                "completa": p["completa"],
                "respondida": vigente is not None,
                "vigente": (vigente or {}).get("respuesta", ""),
            }
        )
    return [{"grupo": g, "preguntas": por_grupo[g]} for g in GRUPOS]
