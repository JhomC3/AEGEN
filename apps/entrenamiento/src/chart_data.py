"""Datos para graficas: raw, cohortes y PFR (spec 008)."""

import pandas as pd

from src.db_connection import read_connection
from src.metrics_engine import RM_FACTOR, calculate_pfr_timeline, rm_ajustado
from src.summary_service import (
    _PeriodTotals,
    aggregate_sets,
    day_label,
    month_label,
    totals_by_period,
    week_label,
)


def _scope_for_filter(
    filter_type: str, filter_value: str | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Ámbito (músculos, ejercicios) del camino único de agregación.

    Extraído para compartir UNA agregación entre hover y RIR en el mismo
    recorrido (idéntico ámbito que _hover_totals_for usaba inline).
    """
    if filter_type == "muscle_group" and filter_value:
        return ((filter_value,), ())
    if filter_type == "exercise" and filter_value:
        return ((), (filter_value,))
    return ((), ())


def _hover_totals_for(
    db_path: str,
    filter_type: str,
    filter_value: str | None,
    granularity: str,
    baselines: dict[str, float] | None = None,
) -> dict[int, _PeriodTotals]:
    """Totales por periodo desde el camino compartido (summary_service).

    Reutiliza aggregate_sets + totals_by_period: cero SQL ni agregación
    duplicada. Devuelve {sort_key: _PeriodTotals}.
    """
    muscles, exercises = _scope_for_filter(filter_type, filter_value)
    aggs = aggregate_sets(db_path, muscles, exercises, granularity, None, None, baselines=baselines)
    return totals_by_period(aggs)


def get_exercise_raw_data(db_path: str, ejercicio: str) -> pd.DataFrame:
    """Retorna datos del ejercicio con contexto de posición y serie.

    La posición se deriva del orden de la primera serie de cada ejercicio en
    la sesión, de modo que ejercicios hechos en distinto estado de fatiga no
    se mezclen en la misma cohorte comparativa.
    """
    with read_connection(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT semana, dia, fecha, set_orden, ejercicio, kg, reps, rir, descanso_seg
            FROM training_sets
            WHERE kg IS NOT NULL AND reps IS NOT NULL
            ORDER BY semana, fecha, set_orden
        """,
            conn,
        )

    if df.empty:
        return df

    df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%Y-%m-%d", errors="coerce")
    session_keys = ["semana", "fecha"]
    df["sesion"] = df.groupby("semana")["fecha_dt"].transform(
        lambda x: x.rank(method="dense").astype(int)
    )
    first_order = df.groupby(session_keys + ["ejercicio"], as_index=False)["set_orden"].min()
    first_order["posicion_ejercicio"] = (
        first_order.groupby(session_keys)["set_orden"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )
    df = df.merge(
        first_order.drop(columns=["set_orden"]),
        on=session_keys + ["ejercicio"],
        how="left",
    )
    df["serie"] = df.groupby(["semana", "fecha", "ejercicio"]).cumcount() + 1
    df = df[df["ejercicio"].str.lower() == ejercicio.lower()].copy()
    if df.empty:
        return df

    rir_safe = df["rir"].fillna(0)
    df["rm"] = (df["kg"] * (1 + RM_FACTOR * df["reps"])).round(1)
    # RM ajustado centralizado (única fuente: metrics_engine.rm_ajustado);
    # RIR ausente cuenta como 0 (semántica vigente del dominio).
    df["rm_ajustado"] = df.apply(
        lambda r: round(
            rm_ajustado(float(r["kg"]), float(r["reps"]), float(rir_safe.loc[r.name])), 1
        ),
        axis=1,
    )

    df = df.sort_values(["semana", "fecha_dt", "serie"]).reset_index(drop=True)
    return df[
        [
            "semana",
            "sesion",
            "serie",
            "fecha",
            "fecha_dt",
            "dia",
            "set_orden",
            "posicion_ejercicio",
            "kg",
            "reps",
            "rir",
            "descanso_seg",
            "rm",
            "rm_ajustado",
        ]
    ]


def get_exercise_cohort_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Resume cohortes homogéneas: posición del ejercicio y serie ordinal.

    El baseline de cada cohorte es su primera observación cronológica. La
    mediana describe el nivel típico y reduce el efecto de una sesión atípica.
    """
    if raw_df.empty:
        return raw_df
    work = raw_df.sort_values(["fecha_dt", "serie"]).copy()
    rows: list[dict[str, object]] = []
    for (position, series), group in work.groupby(["posicion_ejercicio", "serie"], sort=True):
        group = group.sort_values("fecha_dt")
        baseline = float(group.iloc[0]["rm_ajustado"])
        current = float(group.iloc[-1]["rm_ajustado"])
        median = float(group["rm_ajustado"].median())
        rows.append(
            {
                "posicion_ejercicio": int(position),  # type: ignore[call-overload]
                "serie": int(series),  # type: ignore[call-overload]
                "observaciones": len(group),
                "baseline_rm": round(baseline, 1),
                "rm_mediana": round(median, 1),
                "rm_ultima": round(current, 1),
                "crecimiento_pct": round((current / baseline - 1) * 100, 1) if baseline else None,
                "ultima_fecha": group.iloc[-1]["fecha"],
            }
        )
    return pd.DataFrame(rows)


def _pfr_df(
    db_path: str,
    filter_type: str,
    filter_value: str | None,
    granularity: str = "week",
    baselines: dict[str, float] | None = None,
    totals: dict[int, _PeriodTotals] | None = None,
) -> pd.DataFrame:
    """DataFrame de rendimiento por periodo con columnas de hover.

    X/Y provienen de calculate_pfr_timeline (intacto). Las métricas del hover
    (series, reps/peso/RIR medios y RM máximo del periodo) vienen del camino
    ÚNICO de agregación en summary_service (aggregate_sets → totals_by_period).

    Columnas de hover: hlabel (etiqueta centralizada), h_series (int|None),
    h_reps/h_peso/h_rir/h_rm (float|None). None → '—' al renderizar.

    granularity: 'day' | 'week' | 'month'

    ``baselines``/``totals`` opcionales reutilizan cálculos ya hechos por el
    llamante (mismo contenido, cero SQL/agregación duplicada); por defecto se
    calculan como antes.
    """
    df = calculate_pfr_timeline(db_path, filter_type, filter_value, baselines=baselines)
    if df.empty:
        return pd.DataFrame()

    hover = (
        totals
        if totals is not None
        else _hover_totals_for(db_path, filter_type, filter_value, granularity, baselines=baselines)
    )

    def _attach(frame: pd.DataFrame, keys: list[int], labels: list[str]) -> pd.DataFrame:
        """Columnas h_* sin apply por fila: mismo contenido que el camino
        anterior (una Series por fila), pero con listas planas."""
        hits = [hover.get(k) for k in keys]
        cob = list(frame["cobertura"]) if "cobertura" in frame.columns else [None] * len(frame)
        hlabel: list[str] = []
        h_series: list[float | None] = []
        h_reps: list[float | None] = []
        h_peso: list[float | None] = []
        h_rir: list[float | None] = []
        h_rm: list[float | None] = []
        h_cobertura: list[float | None] = []
        for t, b, c in zip(hits, labels, cob):
            if t is None or getattr(t, "series", 0) == 0:
                hlabel.append(b)
                h_series.append(None)
                h_reps.append(None)
                h_peso.append(None)
                h_rir.append(None)
                h_rm.append(None)
                h_cobertura.append(None)
            else:
                hlabel.append(t.label)
                h_series.append(float(t.series))
                h_reps.append(t.reps_media)
                h_peso.append(t.peso_medio)
                h_rir.append(t.rir_medio)
                h_rm.append(t.rm_max)
                h_cobertura.append(c)
        out = frame.copy()
        out["hlabel"] = hlabel
        out["h_series"] = h_series
        out["h_reps"] = h_reps
        out["h_peso"] = h_peso
        out["h_rir"] = h_rir
        out["h_rm"] = h_rm
        out["h_cobertura"] = h_cobertura
        return out

    if granularity == "day":
        # calculate_pfr_timeline devuelve una cronología continua con los días de
        # descanso rellenados (rendimiento ffill, sets_totales=0). Solo mostramos
        # días con entrenamiento real: sin inventar puntos de descanso (req. 2-3).
        result = df[df["sets_totales"] > 0][
            ["fecha_dt", "rendimiento", "sets_totales", "cobertura"]
        ].copy()
        result = result.rename(columns={"sets_totales": "series"})
        result["periodo"] = result["fecha_dt"].dt.strftime("%Y-%m-%d")
        result = result.sort_values("periodo")
        result["crecimiento"] = result["rendimiento"] - 100
        fechas = list(result["fecha_dt"].dt.date)
        return _attach(
            result,
            [d.toordinal() for d in fechas],
            [day_label(d) for d in fechas],
        )

    if granularity == "month":
        df["periodo"] = df["fecha_dt"].dt.to_period("M").astype(str)
        grouped = (
            df.groupby("periodo")
            .agg(
                rendimiento=("rendimiento", "mean"),
                series=("sets_totales", "sum"),
                cobertura=("cobertura", "mean"),
            )
            .reset_index()
            .sort_values("periodo")
        )
        grouped["crecimiento"] = grouped["rendimiento"] - 100
        isos = [str(p) for p in grouped["periodo"]]
        return _attach(
            grouped,
            [int(p.replace("-", "")[:6]) for p in isos],
            [month_label(int(p[:4]), int(p[5:7])) for p in isos],
        )

    # Default: week (comportamiento original)
    weekly = (
        df.groupby("semana")
        .agg(
            rendimiento=("rendimiento", "mean"),
            series=("sets_totales", "sum"),
            cobertura=("cobertura", "mean"),
        )
        .reset_index()
        .dropna(subset=["semana"])
    )
    weekly["semana"] = weekly["semana"].astype(int)
    weekly = weekly.sort_values("semana")
    weekly["crecimiento"] = weekly["rendimiento"] - 100
    weekly["periodo"] = weekly["semana"].astype(str)
    sems = list(weekly["semana"])
    return _attach(
        weekly,
        [int(s) for s in sems],
        [week_label(int(s)) for s in sems],
    )


# Legacy alias
def _weekly_pfr_df(db_path: str, filter_type: str, filter_value: str | None) -> pd.DataFrame:
    return _pfr_df(db_path, filter_type, filter_value, granularity="week")
