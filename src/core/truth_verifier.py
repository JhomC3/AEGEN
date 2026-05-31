# src/core/truth_verifier.py
"""
Verificador de Verdad.

Proceso de auto-critica contra la Boveda de Conocimiento.
Verifica que las afirmaciones del LLM sean consistentes con
los hechos almacenados en la memoria del usuario.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def verify_claim_against_knowledge(
    claim: str,
    chat_id: str,
    store: Any | None = None,
    threshold: float = 0.6,
) -> dict:
    """
    Verifica una afirmacion contra el conocimiento almacenado.

    Args:
        claim: La afirmacion a verificar.
        chat_id: ID del chat del usuario.
        store: SQLite store (inyectado).
        threshold: Umbral de confianza para considerar verificado.

    Returns:
        Dict con:
        - is_verified: bool
        - confidence: float
        - supporting_facts: list[dict]
        - contradicting_facts: list[dict]
        - verdict: str ("verified", "contradicted", "unknown")
    """
    from src.core.dependencies import get_sqlite_store

    if store is None:
        store = get_sqlite_store()

    # Fetch matching memories for comparison
    db = await store.get_db()
    async with db.execute(
        "SELECT id, content, confidence FROM memories "
        "WHERE chat_id LIKE ? AND is_active = 1 "
        "AND content LIKE ? LIMIT 5",
        (f"%{chat_id}%", f"%{claim[:50]}%"),
    ) as cursor:
        rows = await cursor.fetchall()

    results = [{"id": r[0], "content": r[1], "score": r[2]} for r in rows]

    if not results:
        return {
            "is_verified": False,
            "confidence": 0.0,
            "supporting_facts": [],
            "contradicting_facts": [],
            "verdict": "unknown",
        }

    supporting = []
    contradicting = []

    for r in results:
        content = r.get("content", "").lower()
        claim_lower = claim.lower()

        words_in_common = len(set(content.split()) & set(claim_lower.split()))
        total_words = len(set(claim_lower.split()))
        overlap = words_in_common / total_words if total_words > 0 else 0

        if overlap >= threshold:
            supporting.append(r)
        else:
            contradicting.append(r)

    max_confidence = max((r.get("score", 0.0) for r in supporting), default=0.0)

    if supporting and max_confidence >= threshold:
        verdict = "verified"
    elif contradicting and not supporting:
        verdict = "contradicted"
    else:
        verdict = "unknown"

    return {
        "is_verified": verdict == "verified",
        "confidence": max_confidence,
        "supporting_facts": supporting,
        "contradicting_facts": contradicting,
        "verdict": verdict,
    }
