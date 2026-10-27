"""Rutas UI de Rumbo simple: identidad, día 1–10 y tendencia (spec 019)."""

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse

from src import web_context
from src.http_shared import _domain_error_response, _today_iso
from src.models import RumboDiaInput, RumboYoInput, ValidationError
from src.mutation_service import (
    save_rumbo_dia_with_undo_snapshot,
    save_rumbo_respuesta_with_undo_snapshot,
    save_rumbo_yo_with_undo_snapshot,
)
from src.response_fragments import fragment_oob, notice_oob
from src.rumbo_simple_service import parse_fecha
from src.ui_fragments import (
    _rumbo_anual_html,
    _rumbo_hoy_html,
    _rumbo_page_html,
    _rumbo_pregunta_dialog_html,
    _rumbo_preguntas_html,
    _rumbo_semana_html,
    _rumbo_yo_html,
)
from src.web_context import templates

router = APIRouter()

MAX_RUMBO_TEXTO = 500
MAX_RUMBO_RESPUESTA = 2000


def _fecha_o_hoy(fecha: str | None) -> str:
    if not fecha:
        return _today_iso()
    try:
        return parse_fecha(fecha)
    except ValidationError:
        return _today_iso()


@router.get("/rumbo", response_class=HTMLResponse)
def rumbo_view(request: Request, fecha: str | None = Query(None)):
    return HTMLResponse(content=_rumbo_page_html(request, _fecha_o_hoy(fecha)))


@router.post("/rumbo/yo", response_class=HTMLResponse)
def rumbo_yo_guardar(
    request: Request,
    fecha: str = Form(...),
    quien_soy: str = Form(default="", max_length=MAX_RUMBO_TEXTO),
    quien_no: str = Form(default="", max_length=MAX_RUMBO_TEXTO),
    construyendo: str = Form(default="", max_length=MAX_RUMBO_TEXTO),
    t1_nombre: str = Form(default="Tarea 1", max_length=100),
    t2_nombre: str = Form(default="Tarea 2", max_length=100),
    t3_nombre: str = Form(default="Tarea 3", max_length=100),
):
    try:
        fecha_iso = parse_fecha(fecha)
        save_rumbo_yo_with_undo_snapshot(
            web_context.DB_PATH,
            RumboYoInput(
                quien_soy=quien_soy,
                quien_no=quien_no,
                construyendo=construyendo,
                t1_nombre=t1_nombre,
                t2_nombre=t2_nombre,
                t3_nombre=t3_nombre,
            ),
        )
    except Exception as e:
        return _domain_error_response(request, e, "notice-container")
    return HTMLResponse(
        content=notice_oob(templates, request, target="notice-container", message="Rumbo guardado.")
        + fragment_oob(
            templates, request, "rumbo-yo", _rumbo_yo_html(request, fecha_iso), swap="outerHTML"
        )
    )


@router.post("/rumbo/dia", response_class=HTMLResponse)
def rumbo_dia_guardar(
    request: Request,
    fecha: str = Form(...),
    t1: int = Form(...),
    t2: int = Form(...),
    t3: int = Form(...),
):
    try:
        result = save_rumbo_dia_with_undo_snapshot(
            web_context.DB_PATH, RumboDiaInput(fecha=fecha, t1=t1, t2=t2, t3=t3)
        )
        fecha_iso = result["fecha"]
    except Exception as e:
        return _domain_error_response(request, e, "notice-container")
    return HTMLResponse(
        content=notice_oob(
            templates,
            request,
            target="notice-container",
            message=f"Día registrado: {result['score']}/30.",
        )
        + fragment_oob(
            templates, request, "rumbo-hoy", _rumbo_hoy_html(request, fecha_iso), swap="outerHTML"
        )
        + fragment_oob(
            templates,
            request,
            "rumbo-semana",
            _rumbo_semana_html(request, fecha_iso),
            swap="outerHTML",
        )
        + fragment_oob(
            templates,
            request,
            "rumbo-anual",
            _rumbo_anual_html(request, fecha_iso),
            swap="outerHTML",
        )
    )


@router.get("/rumbo/pregunta/{pregunta_id}", response_class=HTMLResponse)
def rumbo_pregunta(request: Request, pregunta_id: str):
    try:
        html = _rumbo_pregunta_dialog_html(request, pregunta_id)
    except Exception as e:
        return _domain_error_response(request, e, "notice-container")
    return HTMLResponse(content=html)


@router.post("/rumbo/respuesta", response_class=HTMLResponse)
def rumbo_respuesta_guardar(
    request: Request,
    pregunta: str = Form(...),
    respuesta: str = Form(..., max_length=MAX_RUMBO_RESPUESTA),
):
    try:
        save_rumbo_respuesta_with_undo_snapshot(web_context.DB_PATH, pregunta, respuesta)
    except Exception as e:
        return _domain_error_response(request, e, "notice-container")
    return HTMLResponse(
        content=notice_oob(
            templates, request, target="notice-container", message="Respuesta guardada."
        )
        + fragment_oob(
            templates,
            request,
            "rumbo-preguntas",
            _rumbo_preguntas_html(request),
            swap="outerHTML",
        )
    )
