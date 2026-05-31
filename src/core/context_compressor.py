# src/core/context_compressor.py
"""
Compresion de contexto conversacional por LLM.

Cuando el historial se acerca al limite de tokens, resume el bloque medio
preservando los primeros y ultimos mensajes.
"""

import logging

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_LIMIT = 6000
PRESERVE_START = 3
PRESERVE_END = 5


def _estimate_tokens(messages: list[dict]) -> int:
    """Estimacion rapida: chars // 4."""
    return sum(len(m.get("content", "")) for m in messages) // 4


async def compress_context_if_needed(
    messages: list[dict],
    token_limit: int = DEFAULT_TOKEN_LIMIT,
    preserve_start: int = PRESERVE_START,
    preserve_end: int = PRESERVE_END,
) -> list[dict]:
    """
    Comprime el contexto conversacional si supera el 80%% del limite de tokens.

    Args:
        messages: Lista de mensajes de la conversacion.
        token_limit: Limite de tokens del modelo.
        preserve_start: Numero de mensajes iniciales a preservar.
        preserve_end: Numero de mensajes finales a preservar.

    Returns:
        Lista de mensajes (posiblemente con bloque medio comprimido).
    """
    estimated = _estimate_tokens(messages)
    if estimated < token_limit * 0.8:
        return messages

    start = messages[:preserve_start]
    end = messages[-preserve_end:]
    middle = messages[preserve_start : len(messages) - preserve_end]

    if not middle:
        return messages

    logger.info(
        "[COMPRESSOR] Comprimiendo contexto: %d tokens estimados "
        "(limite %d). Bloque medio: %d mensajes.",
        estimated,
        token_limit,
        len(middle),
    )

    summary = await _summarize_messages(middle)
    summary_message = {
        "role": "system",
        "content": f"[Resumen de conversacion anterior]\n{summary}",
    }
    return start + [summary_message] + end


async def _summarize_messages(messages: list[dict]) -> str:
    """Resume el bloque de mensajes usando get_fast_llm."""
    from src.core.engine import get_fast_llm

    formatted = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')[:500]}" for m in messages
    )
    prompt = (
        "Resume esta parte de la conversacion en 3-5 oraciones, "
        "preservando los hechos clave y el contexto emocional:\n\n" + formatted
    )

    try:
        llm = get_fast_llm()
        response = await llm.ainvoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        return str(raw)
    except Exception as e:
        logger.warning("[COMPRESSOR] Error resumiendo contexto: %s", e)
        return f"[{len(messages)} mensajes omitidos por limite de contexto]"
