"""Tests de compresion de contexto conversacional."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_compression_skips_when_under_limit():
    """Si el contexto esta bajo el limite, retornar mensajes sin cambios."""
    from src.core.context_compressor import compress_context_if_needed

    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola!"},
    ]
    result = await compress_context_if_needed(messages, token_limit=10000)
    assert result == messages


@pytest.mark.asyncio
async def test_compression_inserts_summary_when_over_limit():
    """Cuando supera el limite, insertar un mensaje de resumen."""
    from src.core.context_compressor import compress_context_if_needed

    messages = [{"role": "user", "content": "x" * 100}] * 20

    with patch(
        "src.core.context_compressor._summarize_messages",
        new_callable=AsyncMock,
        return_value="Resumen del bloque",
    ):
        result = await compress_context_if_needed(messages, token_limit=100)

    summary_msgs = [
        m for m in result if "Resumen de conversacion anterior" in m.get("content", "")
    ]
    assert len(summary_msgs) == 1
    assert len(result) < len(messages)
