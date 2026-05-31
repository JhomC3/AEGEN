# src/tools/session_search.py
"""
Session Search Tool — Busqueda en historial de conversaciones via FTS5.

Permite a MAGI consultar conversaciones pasadas cuando el usuario pregunta
por algo que se discutio en sesiones anteriores.
"""

import logging
from datetime import UTC, datetime, timedelta

from langchain_core.tools import tool

from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


async def _keyword_search_conversations(
    query: str,
    namespace: str,
    days_back: int,
    limit: int,
    store: SQLiteStore | None = None,
) -> list[dict]:
    """
    Busca en conversaciones usando FTS5 con filtro por tipo y fecha en SQL.
    """
    from src.core.dependencies import get_sqlite_store

    if store is None:
        store = get_sqlite_store()

    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()

    sql = """
        SELECT m.id, m.content, m.created_at, m.memory_type
        FROM memories m
        JOIN memories_fts fts ON m.id = fts.rowid
        WHERE m.namespace = ?
          AND m.is_active = 1
          AND m.memory_type = 'conversation'
          AND m.created_at >= ?
          AND fts.content MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        db = await store.get_db()
        cursor = await db.execute(sql, [namespace, cutoff, query, limit])
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "content": r[1],
                "created_at": r[2],
                "memory_type": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("[SESSION-SEARCH] Error en busqueda FTS5: %s", e)
        return []


def _format_conversation_results(results: list[dict]) -> str:
    """Formatea resultados de conversacion para el prompt."""
    if not results:
        return "No encontre conversaciones relevantes en el periodo solicitado."

    lines = [
        f"Encontre {len(results)} fragmento(s) relevante(s) "
        f"de conversaciones previas:\n"
    ]
    for i, r in enumerate(results, 1):
        content = r.get("content", "")[:300]
        created = r.get("created_at", "")[:10]
        lines.append(f"{i}. [{created}] {content}")

    return "\n".join(lines)


@tool
async def search_conversation_history(
    query: str,
    chat_id: str,
    days_back: int = 30,
) -> str:
    """
    Busca en el historial de conversaciones del usuario por palabras clave.

    Usar cuando el usuario pregunta por algo que se discutio en sesiones
    anteriores. Ejemplos: 'que hablamos sobre mi dieta la semana pasada?',
    'recuerdas cuando mencione el gimnasio?'

    Args:
        query: Terminos de busqueda (palabras clave del tema a buscar).
        chat_id: ID del chat del usuario.
        days_back: Numero de dias hacia atras a buscar (default: 30).

    Returns:
        Fragmentos de conversacion relevantes formateados como texto.
    """
    try:
        results = await _keyword_search_conversations(
            query=query,
            namespace=f"user_{chat_id}",
            days_back=days_back,
            limit=5,
        )
        return _format_conversation_results(results)
    except Exception as e:
        logger.warning("[SESSION-SEARCH] Error buscando conversaciones: %s", e)
        return "No pude buscar en el historial en este momento."
