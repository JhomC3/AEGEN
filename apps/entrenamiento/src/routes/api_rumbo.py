"""API v1 JSON de Rumbo simple (aditiva, fusión SDD 001).

Espejo JSON de `ui_rumbo.py`: mismas validaciones, servicios y snapshots de
undo; sin cambiar la UI. Auth `X-Sync-Token` como el resto de la API v1.
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src import web_context
from src.db_rumbo_simple import get_dia, get_yo
from src.http_shared import (
    TRAINING_API_SCHEMA_VERSION,
    _api_domain_error,
    _require_training_api_token,
    hash_estado,
)
from src.models import RumboDiaInput, RumboYoInput
from src.mutation_service import (
    save_rumbo_dia_with_undo_snapshot,
    save_rumbo_respuesta_with_undo_snapshot,
    save_rumbo_yo_with_undo_snapshot,
)
from src.rumbo_simple_service import (
    historial_pregunta,
    parse_fecha,
    preguntas_con_estado,
    score_semana,
    serie_anual_52,
    vigente_pregunta,
)

router = APIRouter()
_LOG = "rumbo_api"


def _ok(fecha: str, **extra) -> JSONResponse:
    payload = {"schema_version": TRAINING_API_SCHEMA_VERSION, "fecha": fecha}
    payload.update(extra)
    return JSONResponse(payload)


@router.get("/api/v1/rumbo/dia")
def api_rumbo_dia(request: Request, fecha: str = Query(default="")):
    """Identidad + día + semana + serie anual para una fecha."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        fecha_iso = parse_fecha(fecha) if fecha and fecha.strip() else None
        if fecha_iso is None:
            from src.http_shared import _today_iso

            fecha_iso = _today_iso()
        dia = get_dia(web_context.DB_PATH, fecha_iso)
        return _ok(
            fecha_iso,
            yo=get_yo(web_context.DB_PATH),
            dia=dia,
            semana=score_semana(web_context.DB_PATH, fecha_iso),
            serie_anual=serie_anual_52(web_context.DB_PATH, fecha_iso),
            base_hash=hash_estado(dia),
        )
    except Exception as exc:
        return _api_domain_error(exc, _LOG)


@router.post("/api/v1/rumbo/dia")
async def api_rumbo_dia_guardar(request: Request):
    """Guarda el día (t1/t2/t3 1–10) con snapshot de undo. Reemplazo del día."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        result = save_rumbo_dia_with_undo_snapshot(
            web_context.DB_PATH,
            RumboDiaInput(
                fecha=body.get("fecha", ""),
                t1=body.get("t1"),
                t2=body.get("t2"),
                t3=body.get("t3"),
            ),
            base_hash=body.get("base_hash"),
        )
        return _ok(
            result["fecha"],
            t1=result["t1"],
            t2=result["t2"],
            t3=result["t3"],
            score=result["score"],
            saved=True,
            base_hash=hash_estado(get_dia(web_context.DB_PATH, result["fecha"])),
        )
    except Exception as exc:
        return _api_domain_error(exc, _LOG)


@router.post("/api/v1/rumbo/yo")
async def api_rumbo_yo_guardar(request: Request):
    """Guarda la identidad con snapshot de undo."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        result = save_rumbo_yo_with_undo_snapshot(
            web_context.DB_PATH,
            RumboYoInput(
                quien_soy=body.get("quien_soy", ""),
                quien_no=body.get("quien_no", ""),
                construyendo=body.get("construyendo", ""),
                t1_nombre=body.get("t1_nombre", "Tarea 1"),
                t2_nombre=body.get("t2_nombre", "Tarea 2"),
                t3_nombre=body.get("t3_nombre", "Tarea 3"),
            ),
        )
        return _ok(result.get("fecha", ""), yo=result, saved=True)
    except Exception as exc:
        return _api_domain_error(exc, _LOG)


@router.get("/api/v1/rumbo/preguntas")
def api_rumbo_preguntas(request: Request):
    """Catálogo de 36 preguntas con estado de respuesta."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        preguntas = preguntas_con_estado(web_context.DB_PATH)
        return JSONResponse(
            {
                "schema_version": TRAINING_API_SCHEMA_VERSION,
                "count": len(preguntas),
                "preguntas": preguntas,
            }
        )
    except Exception as exc:
        return _api_domain_error(exc, _LOG)


@router.get("/api/v1/rumbo/respuestas")
def api_rumbo_respuestas(request: Request, pregunta: str = Query(default="")):
    """Vigente + historial de una pregunta."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        if not pregunta or not pregunta.strip():
            return JSONResponse({"detail": "Pregunta requerida."}, status_code=400)
        return JSONResponse(
            {
                "schema_version": TRAINING_API_SCHEMA_VERSION,
                "pregunta": pregunta.strip(),
                "vigente": vigente_pregunta(web_context.DB_PATH, pregunta.strip()),
                "historial": historial_pregunta(web_context.DB_PATH, pregunta.strip()),
            }
        )
    except Exception as exc:
        return _api_domain_error(exc, _LOG)


@router.post("/api/v1/rumbo/respuesta")
async def api_rumbo_respuesta_guardar(request: Request):
    """Guarda una respuesta con snapshot de undo."""
    auth_error = _require_training_api_token(request)
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        result = save_rumbo_respuesta_with_undo_snapshot(
            web_context.DB_PATH, body.get("pregunta", ""), body.get("respuesta", "")
        )
        return JSONResponse(
            {
                "schema_version": TRAINING_API_SCHEMA_VERSION,
                "id": result["id"],
                "pregunta": result["pregunta"],
                "saved": True,
            }
        )
    except Exception as exc:
        return _api_domain_error(exc, _LOG)
