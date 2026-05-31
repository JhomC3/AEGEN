# src/core/insights_engine.py
"""
Insights Engine — Dashboard de analitica de uso.

Provee metricas de uso: modelos mas usados, costos, skills mas
cargadas, tokens por sesion, patrones de actividad.
"""

# ruff: noqa: S608  # Parameterized queries, not user input
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


async def get_usage_insights(
    chat_id: str | None = None,
    days_back: int = 7,
    store: Any | None = None,
    redis_conn: Any | None = None,
) -> dict:
    """
    Genera un reporte de insights de uso del sistema.

    Args:
        chat_id: Si se proporciona, filtra por usuario especifico.
        days_back: Numero de dias hacia atras para el analisis.
        store: SQLite store (inyectado).
        redis_conn: Redis connection (inyectado).

    Returns:
        Dict con insights de uso.
    """
    from src.core.dependencies import get_sqlite_store, redis_connection

    if store is None:
        store = get_sqlite_store()
    if redis_conn is None:
        redis_conn = redis_connection

    cutoff = (
        datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    )

    insights = {
        "generated_at": datetime.now(UTC).isoformat(),
        "period_days": days_back,
        "total_sessions": 0,
        "total_messages": 0,
        "most_used_models": [],
        "total_cost_usd": 0.0,
        "most_loaded_skills": [],
        "activity_pattern": {},
        "top_intents": [],
    }

    try:
        db = await store.get_db()

        where_clause = "WHERE created_at >= ?"
        params: list = [cutoff]

        if chat_id:
            where_clause += " AND chat_id = ?"
            params.append(chat_id)

        async with db.execute(
            f"SELECT COUNT(DISTINCT chat_id) FROM memories {where_clause}",
            params,
        ) as cursor:
            row = await cursor.fetchone()
            insights["total_sessions"] = row[0] if row else 0

        async with db.execute(
            f"SELECT COUNT(*) FROM memories {where_clause}",
            params,
        ) as cursor:
            row = await cursor.fetchone()
            insights["total_messages"] = row[0] if row else 0

        async with db.execute(
            f"SELECT memory_type, COUNT(*) as cnt FROM memories "
            f"{where_clause} GROUP BY memory_type ORDER BY cnt DESC LIMIT 5",
            params,
        ) as cursor:
            rows = await cursor.fetchall()
            insights["most_used_models"] = [{"type": r[0], "count": r[1]} for r in rows]

        async with db.execute(
            f"SELECT source_skill, COUNT(*) as cnt FROM memories "
            f"{where_clause} AND source_skill IS NOT NULL "
            f"GROUP BY source_skill ORDER BY cnt DESC LIMIT 5",
            params,
        ) as cursor:
            rows = await cursor.fetchall()
            insights["most_loaded_skills"] = [
                {"skill": r[0], "count": r[1]} for r in rows
            ]

        async with db.execute(
            f"SELECT strftime('%w', created_at) as dow, COUNT(*) as cnt "
            f"FROM memories {where_clause} GROUP BY dow ORDER BY dow",
            params,
        ) as cursor:
            rows = await cursor.fetchall()
            day_names = [
                "domingo",
                "lunes",
                "martes",
                "miercoles",
                "jueves",
                "viernes",
                "sabado",
            ]
            insights["activity_pattern"] = {day_names[int(r[0])]: r[1] for r in rows}

    except Exception as e:
        logger.warning("[INSIGHTS] Error generando insights: %s", e)

    if redis_conn:
        try:
            keys = await redis_conn.keys("llm:metrics:*")
            total_cost = 0.0
            for key in keys:
                val = await redis_conn.get(key)
                if val:
                    try:
                        import json

                        data = json.loads(val)
                        total_cost += data.get("cost", 0.0)
                    except Exception:
                        logger.debug("[INSIGHTS] Error parsing metric: %s", key)
            insights["total_cost_usd"] = round(total_cost, 4)
        except Exception as e:
            logger.warning("[INSIGHTS] Error leyendo costos de Redis: %s", e)

    return insights
