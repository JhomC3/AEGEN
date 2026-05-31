"""Tests del nudge de memoria post-turno."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_redis(incr_value: int) -> MagicMock:
    """Crea un mock de Redis con incr y expire como AsyncMock."""
    mock = MagicMock()
    mock.incr = AsyncMock(return_value=incr_value)
    mock.expire = AsyncMock(return_value=True)
    mock.lrange = AsyncMock(return_value=[])
    return mock


@pytest.mark.asyncio
async def test_nudge_skips_if_not_nudge_turn() -> None:
    """El nudge solo se activa cada N turnos."""
    from src.memory.nudge_worker import memory_nudge_worker

    mock_redis = _make_mock_redis(incr_value=2)

    result = await memory_nudge_worker(
        chat_id="123", nudge_every_n=3, redis_conn=mock_redis
    )

    assert result == {"extracted": 0, "reason": "not_nudge_turn"}


@pytest.mark.asyncio
async def test_nudge_extracts_facts_on_nudge_turn() -> None:
    """En el turno de nudge, extrae hechos y los persiste."""
    from src.memory.nudge_worker import memory_nudge_worker

    mock_facts = [
        {
            "content": "Prefiere sesiones de 45 minutos",
            "type": "preference",
            "confidence": 0.85,
        },
    ]

    mock_redis = _make_mock_redis(incr_value=3)
    mock_store = MagicMock()

    with (
        patch(
            "src.memory.nudge_worker._get_recent_messages",
            new_callable=AsyncMock,
            return_value=[
                {"role": "user", "content": "Prefiero sesiones de 45 minutos"}
            ],
        ),
        patch(
            "src.memory.nudge_worker._extract_lightweight_facts",
            new_callable=AsyncMock,
            return_value=mock_facts,
        ) as mock_extract,
        patch(
            "src.memory.nudge_worker._save_fact_if_new",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_save,
    ):
        result = await memory_nudge_worker(
            chat_id="123",
            nudge_every_n=3,
            redis_conn=mock_redis,
            store=mock_store,
        )

    mock_extract.assert_awaited_once()
    mock_save.assert_awaited_once()
    assert result["extracted"] == 1


@pytest.mark.asyncio
async def test_nudge_deduplicates_existing_facts() -> None:
    """No persiste facts que ya existen."""
    from src.memory.nudge_worker import memory_nudge_worker

    mock_redis = _make_mock_redis(incr_value=3)
    mock_store = MagicMock()

    with (
        patch(
            "src.memory.nudge_worker._get_recent_messages",
            new_callable=AsyncMock,
            return_value=[{"role": "user", "content": "Prefiero mananas"}],
        ),
        patch(
            "src.memory.nudge_worker._extract_lightweight_facts",
            new_callable=AsyncMock,
            return_value=[{"content": "Prefiere mananas", "type": "preference"}],
        ),
        patch(
            "src.memory.nudge_worker._save_fact_if_new",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        result = await memory_nudge_worker(
            chat_id="123",
            nudge_every_n=3,
            redis_conn=mock_redis,
            store=mock_store,
        )

    assert result["extracted"] == 0
