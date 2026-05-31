# src/agents/workers/life_review.py
"""
Agente de Revision de Vida (Life Review).

Analiza historiales masivos para extraer hitos, valores y
patrones del perfil del usuario.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

LIFE_REVIEW_PROMPT = """
Eres un experto analista biografico. Analiza la siguiente conversacion
historica del usuario y extrae:

1. HITOS: Eventos importantes (cambios de vida, logros, perdidas)
2. VALORES: Principios fundamentales que guian sus decisiones
3. PATRONES: Comportamientos recurrentes (positivos y negativos)
4. RELACIONES: Personas significativas mencionadas
5. METAS: Objetivos explicitos o implicitos

Responde SOLO con un JSON estructurado:
{{
  "milestones": [{{"event": "...", "date_approx": "...", "impact": "high|medium|low"}}],
  "values": ["valor1", "valor2"],
  "patterns": [{{"pattern": "...", "type": "positive|negative"}}],
  "relationships": [{{"person": "...", "role": "...", "sentiment": "positive|negative|neutral"}}],
  "goals": [{{"goal": "...", "status": "active|completed|abandoned"}}]
}}

CONVERSACION:
{conversation}
"""


async def run_life_review(
    chat_id: str,
    messages: list[dict],
    store: Any | None = None,
) -> dict[str, Any]:
    """
    Ejecuta el analisis de revision de vida sobre un historial.

    Args:
        chat_id: ID del chat del usuario.
        messages: Lista de mensajes historicos.
        store: SQLite store (inyectado).

    Returns:
        Dict con hitos, valores, patrones, relaciones y metas.
    """
    import json

    from src.core.engine import get_analytical_llm

    conv_text = "\n".join([
        f"{m.get('role', 'user')}: {m.get('content', '')[:500]}"
        for m in messages[-100:]
    ])

    prompt = LIFE_REVIEW_PROMPT.format(conversation=conv_text)

    try:
        llm = get_analytical_llm()
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        start = content.find("{")
        end = content.rfind("}") + 1
        if start < 0 or end <= start:
            logger.warning("[LIFE-REVIEW] No se encontro JSON valido en la respuesta")
            return {"error": "No se pudo parsear la respuesta"}

        result: dict[str, Any] = json.loads(content[start:end])

        if store:
            await _save_life_review_results(chat_id, result, store)

        logger.info(
            "[LIFE-REVIEW] Analisis completado para %s: "
            "%d hitos, %d valores, %d patrones",
            chat_id,
            len(result.get("milestones", [])),
            len(result.get("values", [])),
            len(result.get("patterns", [])),
        )

        return result

    except Exception as e:
        logger.error("[LIFE-REVIEW] Error: %s", e, exc_info=True)
        return {"error": str(e)}


async def _save_life_review_results(chat_id: str, results: dict, store: Any) -> None:
    """Guarda los resultados del life review como facts estructurados."""
    db = await store.get_db()

    for milestone in results.get("milestones", []):
        await db.execute(
            "INSERT INTO memories "
            "(chat_id, content, memory_type, namespace, metadata, "
            "confidence, source_type, is_active) "
            "VALUES (?, ?, 'milestone', ?, ?, 0.8, 'life_review', 1)",
            (
                chat_id,
                f"Hito: {milestone.get('event', '')}",
                f"user_{chat_id}",
                json.dumps({
                    "date_approx": milestone.get("date_approx"),
                    "impact": milestone.get("impact"),
                }),
            ),
        )

    for value in results.get("values", []):
        await db.execute(
            "INSERT INTO memories "
            "(chat_id, content, memory_type, namespace, metadata, "
            "confidence, source_type, is_active) "
            "VALUES (?, ?, 'value', ?, ?, 0.7, 'life_review', 1)",
            (
                chat_id,
                f"Valor: {value}",
                f"user_{chat_id}",
                json.dumps({}),
            ),
        )

    for pattern in results.get("patterns", []):
        await db.execute(
            "INSERT INTO memories "
            "(chat_id, content, memory_type, namespace, metadata, "
            "confidence, source_type, is_active) "
            "VALUES (?, ?, 'pattern', ?, ?, 0.6, 'life_review', 1)",
            (
                chat_id,
                f"Patron ({pattern.get('type', 'unknown')}): "
                f"{pattern.get('pattern', '')}",
                f"user_{chat_id}",
                json.dumps({"type": pattern.get("type")}),
            ),
        )

    await db.commit()
