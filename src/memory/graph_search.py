# src/memory/graph_search.py
import logging
from typing import Any

from src.memory.json_sanitizer import safe_json_loads
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


async def expand_with_edges(
    store: SQLiteStore,
    seed_memory_ids: list[int],
    max_hops: int = 2,
    relation_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Dado un conjunto de memory IDs semilla (resultado del Two-Stage Retrieval),
    expande el grafo horizontalmente usando memory_edges con un límite fijo de max_hops (límite hard = 2).

    Retorna los recuerdos del sub-grafo con su peso de relevancia acumulada.
    """
    if not seed_memory_ids:
        return []

    # Límite hard de 2 saltos máximo por requerimientos de latencia en SQLite (ADR-0033)
    hops = min(max(1, max_hops), 2)
    db = await store.get_db()

    # Preparar parámetros para SQLite
    placeholder_seeds = ",".join(["?"] * len(seed_memory_ids))
    params: list[Any] = list(seed_memory_ids)

    # Lógica condicional por tipo de relación
    relation_filter = ""
    if relation_types:
        relation_filter = (
            "AND e.tipo_relacion IN (" + ",".join(["?"] * len(relation_types)) + ")"
        )
        params.extend(relation_types)

    # Query CTE recursiva para expansión transversal (ADR-0033)
    sql_cte = f"""  # noqa: S608
    WITH RECURSIVE subgraph(memory_id, depth, accumulated_weight) AS (
        -- Semilla: los IDs del RAG inicial
        SELECT id, 0, 1.0 FROM memories WHERE id IN ({placeholder_seeds}) AND is_active = 1
        UNION ALL
        SELECT e.destino_id, s.depth + 1, s.accumulated_weight * e.peso
        FROM memory_edges e
        JOIN subgraph s ON e.origen_id = s.memory_id
        WHERE s.depth < ? {relation_filter}
    )
    SELECT g.memory_id, MAX(g.accumulated_weight) as relevance, m.chat_id, m.content, m.memory_type, m.metadata
    FROM subgraph g
    JOIN memories m ON g.memory_id = m.id
    WHERE m.is_active = 1 AND g.memory_id NOT IN ({placeholder_seeds})
    GROUP BY g.memory_id
    ORDER BY relevance DESC
    """

    # Añadimos el parámetro de profundidad a params
    params_final = params[: len(seed_memory_ids)] + [hops]
    if relation_types:
        params_final.extend(relation_types)
    params_final.extend(seed_memory_ids)  # para la exclusión de la semilla final NOT IN

    results = []
    try:
        async with db.execute(sql_cte, params_final) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append({
                    "id": r[0],
                    "score": round(r[1], 4),
                    "chat_id": r[2],
                    "content": r[3],
                    "memory_type": r[4],
                    "metadata": safe_json_loads(r[5]) or {},
                    "hop_distance": True,  # Indicador de que es una expansión del grafo
                })

        logger.debug(
            f"[GRAPH-SEARCH] Expanded seed {seed_memory_ids} into {len(results)} transversal fragments."
        )
        return results

    except Exception as e:
        logger.error(f"[GRAPH-SEARCH] Failed CTE recursion search: {e}", exc_info=True)
        return []
