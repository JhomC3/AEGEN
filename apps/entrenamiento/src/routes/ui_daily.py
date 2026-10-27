"""Rutas UI diarias: indice y diario (spec 009; cardio retirado en spec 017)."""

from datetime import date

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import MUSCLE_CATEGORIES
from src import web_context
from src.charts import (
    chart_metrics_index,
    chart_pfr_timeline,
    chart_selection,
)
from src.dashboard_service import (
    chart_shell_html,
    get_filters,
)
from src.database import (
    get_categories,
    get_dashboard_catalog,
    get_diario_by_fecha,
    get_ejercicio_categoria,
    get_plantillas_alimentacion,
    get_sets_by_fecha,
)
from src.http_shared import (
    _today_iso,
    _validate_granularity,
    _validate_window,
)
from src.security import (
    get_csrf_secret,
    make_csrf_token,
)
from src.training_service import (
    calculate_cycle_week,
    day_from_date,
    fecha_display,
    fecha_to_db,
)
from src.ui_fragments import (
    _alimento_form_html,
    _alimento_preview_map,
    _cascade_row_html,
    _daily_app_config,
    _editor_html,
    _exercise_form_html,
    _navigator_html,
    _nutrition_editor_html,
    _plantillas_alimentacion_list_html,
    _plantillas_list_html,
    _render_body,
)
from src.web_context import CICLO_START_DATE, templates

router = APIRouter()


def _clean_selection(values: list[str]) -> list[str]:
    """Normaliza una selección de la URL: acepta coma o repetidos, strip y
    dedupe conservando el orden (misma regla que la cascada cliente)."""
    out: list[str] = []
    for raw in values:
        for part in str(raw).split(","):
            item = part.strip()
            if item and item not in out:
                out.append(item)
    return out


@router.get("/", response_class=HTMLResponse)
def read_index(
    request: Request,
    gran: str = Query(default="day"),
    registro: str = Query(default=""),
    metricas: str | None = Query(default=None),
    musculos: list[str] = Query(default=[]),
    ejercicios: list[str] = Query(default=[]),
    ventana: int = Query(default=8),
):
    from datetime import date as _date

    # ``?registro=`` fue la URL del editor emergente anterior. La conservamos
    # como enlace de compatibilidad, pero la experiencia canónica vive en
    # /diario y no debe volver a abrir una segunda interfaz de registro.
    if registro:
        try:
            legacy_date = _date.fromisoformat(registro)
        except ValueError:
            legacy_date = None
        if legacy_date is not None:
            return RedirectResponse(url=f"/diario?fecha={legacy_date.isoformat()}", status_code=303)

    from src.metrics_engine import get_exercises_baselines
    from src.summary_service import build_period_summary, db_window

    # Baselines UNA vez por petición: los comparten el resumen, la cronología
    # sistémica, el hover y el RIR (mismo contenido, cero SQL duplicado).
    _shared_baselines = get_exercises_baselines(web_context.DB_PATH)
    ejercicios_list, grupos_list = get_filters(web_context.DB_PATH)
    categories = get_categories(web_context.DB_PATH) or MUSCLE_CATEGORIES
    fecha = _today_iso()
    _fecha_date = _date.fromisoformat(fecha)
    granularity = _validate_granularity(gran)
    semanas = _validate_window(ventana)
    # Selección inicial desde la URL (spec 039 RF-1): misma normalización que
    # la cascada (coma o repetidos, strip, dedupe con orden). Vacía = global.
    sel_musculos = _clean_selection(musculos)
    sel_ejercicios = _clean_selection(ejercicios)
    # Render inicial del panel derecho server-side: sin flash ni layout shift
    # (misma técnica anti-parpadeo de la granularidad). El servicio devuelve
    # estado error/empty controlado; nunca propaga a HTTP.
    period_summary = build_period_summary(
        web_context.DB_PATH,
        sel_musculos,
        sel_ejercicios,
        granularity,
        semanas,
        baselines=_shared_baselines,
    )
    from src.health_panels import (
        build_metrics_catalog,
        build_metrics_index,
        parse_metrics_param,
    )

    # La gráfica de nutrición ES la gráfica de métricas (índice 0–100 con
    # todas las series; valores reales en tooltip). Reutiliza slot, ids y
    # canal OOB de nutrition-trend (cero churn de templates/CSS/JS).
    _metrics_selection = parse_metrics_param(metricas)
    _metrics_df_day = build_metrics_index(web_context.DB_PATH, "day")
    _metrics_df_fig = (
        _metrics_df_day
        if granularity == "day"
        else build_metrics_index(web_context.DB_PATH, granularity)
    )
    _metrics_fig = chart_metrics_index(_metrics_df_fig, granularity, _metrics_selection)
    if sel_musculos:
        _systemic_fig = chart_selection(
            web_context.DB_PATH, sel_musculos, sel_ejercicios, granularity
        )
    else:
        _systemic_fig = chart_pfr_timeline(
            web_context.DB_PATH,
            "systemic",
            "",
            granularity=granularity,
            baselines=_shared_baselines,
        )
    _catalog_window = db_window(web_context.DB_PATH, 8)
    if _catalog_window is not None:
        _dashboard_catalog = get_dashboard_catalog(
            web_context.DB_PATH,
            _catalog_window.start.isoformat(),
            _catalog_window.end.isoformat(),
        )
    else:
        _dashboard_catalog = get_dashboard_catalog(web_context.DB_PATH)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "grupos_list": grupos_list,
            "ejercicios_list": ejercicios_list,
            "ejercicios_grupo": ejercicios_list,
            "muscle_categories": categories,
            "effective_gran": granularity,
            "period_summary": period_summary,
            "dashboard_catalog": _dashboard_catalog,
            "selected_muscles": set(sel_musculos),
            "selected_exercises": set(sel_ejercicios),
            "cascade_row_html": _cascade_row_html(request, "musculo", ""),
            "systemic_chart_html": chart_shell_html(
                "Rendimiento",
                _systemic_fig,
            ),
            "metrics_catalog": build_metrics_catalog(
                web_context.DB_PATH, _metrics_selection, _metrics_df_day
            ),
            "nutrition_trend_html": chart_shell_html(
                "Métricas",
                _metrics_fig,
                empty_text="Sin datos de métricas",
                prefix="nutrition-trend",
            ),
            "navigator_html": _navigator_html(request, fecha, granularity=granularity),
            "editor_html": _editor_html(request, fecha),
            "dia": day_from_date(_fecha_date),
            "fecha_display": fecha_display(fecha),
            "semana": calculate_cycle_week(_fecha_date, CICLO_START_DATE),
            "exercise_form_html": _exercise_form_html(request),
            "plantillas_html": _plantillas_list_html(request),
            "nutrition_editor_html": _nutrition_editor_html(request, fecha),
            "nutrition_templates_html": _plantillas_alimentacion_list_html(request, fecha),
            "alimento_form_html": _alimento_form_html(request),
            "app_config_json": {
                "categoria_map": get_ejercicio_categoria(web_context.DB_PATH),
                "alimento_map": _alimento_preview_map(),
                "ciclo_start": CICLO_START_DATE.isoformat(),
                "csrf_token": make_csrf_token(get_csrf_secret()),
                "seleccion_inicial": {
                    "musculos": sel_musculos,
                    "ejercicios": sel_ejercicios,
                    "gran": granularity,
                    "metricas": list(_metrics_selection),
                    "ventana": semanas,
                },
            },
        },
    )


@router.get("/fecha/editor", response_class=HTMLResponse)
def fecha_editor(request: Request, fecha: str = Query(...)):
    return HTMLResponse(content=_editor_html(request, fecha))


@router.get("/diario", response_class=HTMLResponse)
def diario_page(
    request: Request,
    fecha: str = Query(default=""),
    vista: str = Query(default="entrenamiento"),
):
    """Standalone daily workspace; ``/registro`` remains a compatibility alias."""
    from datetime import date as _date

    if not fecha:
        fecha = _date.today().isoformat()
    if vista not in {"entrenamiento", "alimentacion"}:
        vista = "entrenamiento"
    fecha_date = _date.fromisoformat(fecha)

    session_has_data = bool(get_sets_by_fecha(web_context.DB_PATH, fecha_to_db(fecha_date)))
    food_has_data = bool(get_diario_by_fecha(web_context.DB_PATH, fecha))
    context = {
        "navigator_html": _navigator_html(request, fecha, variant="daily", vista=vista),
        "nutrition_templates_html": _plantillas_alimentacion_list_html(request, fecha),
        "nutrition_editor_html": _nutrition_editor_html(request, fecha),
        "editor_html": _editor_html(request, fecha),
        "exercise_form_html": _exercise_form_html(request),
        "alimento_form_html": _alimento_form_html(request),
        "plantillas_html": _plantillas_list_html(request),
        "dia": day_from_date(fecha_date),
        "fecha_display": fecha_display(fecha),
        "daily_date_title": f"{fecha_date.day:02d}/{fecha_date.month:02d}/{fecha_date.year % 100:02d}",
        "vista": vista,
        "fecha_iso": fecha,
        "session_has_data": session_has_data,
        "food_has_data": food_has_data,
        "food_template_count": len(get_plantillas_alimentacion(web_context.DB_PATH)),
        "app_config_json": _daily_app_config(),
    }
    return HTMLResponse(
        content=_render_body(
            templates.TemplateResponse(request=request, name="diario.html", context=context)
        )
    )


@router.get("/registro", response_class=HTMLResponse)
def registro_legacy(
    fecha: str = Query(default=""),
    vista: str = Query(default="entrenamiento"),
):
    """Redirect the former registro URL to the single canonical Diario page."""
    params = []
    if fecha:
        try:
            fecha = date.fromisoformat(fecha).isoformat()
        except ValueError:
            fecha = ""
    if fecha:
        params.append(f"fecha={fecha}")
    if vista in {"entrenamiento", "alimentacion"}:
        params.append(f"vista={vista}")
    query = "&".join(params)
    return RedirectResponse(url="/diario" + (f"?{query}" if query else ""), status_code=303)


@router.get("/diario/navigator", response_class=HTMLResponse)
def diario_navigator(
    request: Request,
    fecha: str = Query(...),
    vista: str = Query(default="entrenamiento"),
):
    """Fragmento del carrusel de fechas del Diario (variante compacta).

    Los puntos se filtran por ``vista``: entrenamiento o alimentación.
    """
    if vista not in {"entrenamiento", "alimentacion"}:
        vista = "entrenamiento"
    return HTMLResponse(content=_navigator_html(request, fecha, variant="daily", vista=vista))


@router.get("/editor/popup", response_class=HTMLResponse)
def editor_popup(request: Request, fecha: str = Query(...)):
    """Cuerpo de la ventana emergente de registro: navegador + editores."""
    from datetime import date as _date

    fecha_date = _date.fromisoformat(fecha)
    return _render_body(
        templates.TemplateResponse(
            request=request,
            name="editor_popup.html",
            context={
                "navigator_html": _navigator_html(request, fecha, granularity="day"),
                "nutrition_templates_html": _plantillas_alimentacion_list_html(request, fecha),
                "nutrition_editor_html": _nutrition_editor_html(request, fecha),
                "editor_html": _editor_html(request, fecha),
                "exercise_form_html": _exercise_form_html(request),
                "alimento_form_html": _alimento_form_html(request),
                "plantillas_html": _plantillas_list_html(request),
                "dia": day_from_date(fecha_date),
                "fecha_display": fecha_display(fecha),
                "semana": calculate_cycle_week(fecha_date, CICLO_START_DATE),
            },
        )
    )
