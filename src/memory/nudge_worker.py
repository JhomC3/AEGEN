# src/memory/nudge_worker.py
"""
Nudge de Memoria Post-Turno.

Extrae hechos de los ultimos N mensajes cada NUDGE_EVERY_N_TURNS turnos,
complementando el ConsolidationWorker sin reemplazarlo.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

NUDGE_EVERY_N_TURNS: int = 3
_NUDGE_PROMPT = """
Analiza estos mensajes recientes y extrae UNICAMENTE preferencias explicitas
y hechos concretos verificables. NO generes resumenes ni analisis.
Solo hechos directos del usuario.

Mensajes:
{messages}

Responde con una lista JSON de objetos:
[{{"content": "...", "type": "preference|fact", "confidence": 0.0-1.0}}]
Si no hay hechos nuevos dignos de guardar, responde con: []
"""


async def _get_turn_count(chat_id: str, redis_conn: Any) -> int:
    """Incrementa y retorna el contador de turnos del chat."""
    key = f"chat:turn_count:{chat_id}"
    count = await redis_conn.incr(key)
    await redis_conn.expire(key, 86400)
    return int(count)


async def _get_recent_messages(
    chat_id: str, redis_conn: Any, limit: int = 6
) -> list[dict]:
    """Obtiene los ultimos `limit` mensajes del buffer Redis."""
    key = f"chat:buffer:{chat_id}"
    raw = await redis_conn.lrange(key, -limit, -1)
    messages = []
    for item in raw:
        try:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            messages.append(json.loads(item))
        except Exception:
            pass
    return messages


async def _extract_lightweight_facts(messages: list[dict]) -> list[dict]:
    """Usa get_fast_llm para extraer hechos concretos de los mensajes."""
    from src.core.engine import get_fast_llm

    if not messages:
        return []

    formatted = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
    )
    prompt = _NUDGE_PROMPT.format(messages=formatted)

    try:
        llm = get_fast_llm()
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            parsed: list[dict] = json.loads(content[start:end])
            return parsed
    except Exception as e:
        logger.warning("[NUDGE] Error extrayendo facts: %s", e)
    return []


async def _save_fact_if_new(
    chat_id: str,
    fact: dict,
    store: Any,
) -> bool:
    """
    Guarda el fact si no existe uno similar (deduplicacion por FTS5).
    Retorna True si se guardo, False si era duplicado.
    """
    from src.memory.sqlite_store import SQLiteStore

    content = fact.get("content", "")
    if not content:
        return False

    # Simple dedup: check if similar content exists
    db = await store.get_db()
    async with db.execute(
        "SELECT id FROM memories WHERE chat_id = ? AND content LIKE ? LIMIT 1",
        (chat_id, f"%{content[:30]}%"),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            logger.debug("[NUDGE] Fact duplicado: %s", content[:50])
            return False

    from src.memory.ingestion_pipeline import IngestionPipeline

    pipeline = IngestionPipeline(store=store)
    await pipeline.process_text(
        chat_id=chat_id,
        text=content,
        memory_type=fact.get("type", "fact"),
        metadata={"confidence": fact.get("confidence", 0.7)},
    )
    return True


async def memory_nudge_worker(
    chat_id: str,
    nudge_every_n: int = NUDGE_EVERY_N_TURNS,
    redis_conn: Any = None,
    store: Any = None,
) -> dict:
    """
    Worker de nudge de memoria post-turno.

    Args:
        chat_id: ID del chat del usuario.
        nudge_every_n: Activar cada N turnos.
        redis_conn: Conexion Redis (inyectada).
        store: SQLite store (inyectado).

    Returns:
        Dict con resultado: {"extracted": N, "deduplicated": M, "reason": "..."}
    """
    if redis_conn is None:
        from src.core.dependencies import redis_connection

        redis_conn = redis_connection

    if redis_conn is None:
        return {"extracted": 0, "reason": "redis_unavailable"}

    turn_count = await _get_turn_count(chat_id, redis_conn)

    if turn_count % nudge_every_n != 0:
        return {"extracted": 0, "reason": "not_nudge_turn"}

    messages = await _get_recent_messages(chat_id, redis_conn)
    if not messages:
        return {"extracted": 0, "reason": "no_messages"}

    facts = await _extract_lightweight_facts(messages)

    if store is None:
        from src.core.dependencies import get_sqlite_store

        store = get_sqlite_store()

    extracted = 0
    deduplicated = 0
    for fact in facts:
        saved = await _save_fact_if_new(chat_id, fact, store)
        if saved:
            extracted += 1
        else:
            deduplicated += 1

    logger.info(
        "[NUDGE] chat=%s turn=%d: extracted=%d, deduplicated=%d",
        chat_id,
        turn_count,
        extracted,
        deduplicated,
    )
    return {
        "extracted": extracted,
        "deduplicated": deduplicated,
        "reason": "nudge_executed",
    }
