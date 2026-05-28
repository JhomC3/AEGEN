# tests/unit/memory/test_time_decay.py
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.memory.hybrid_search import HybridSearch


@pytest.mark.asyncio
async def test_time_decay_math_logic():
    # Mock SQLiteStore
    store = MagicMock()
    hybrid = HybridSearch(store)

    # 2 mock rows:
    # row1 is 1 day old, row2 is 100 days old
    now = datetime.now(UTC)
    row1_created = (now - timedelta(days=1)).isoformat()
    row2_created = (now - timedelta(days=100)).isoformat()

    results = [
        {
            "id": 1,
            "content": "recent content",
            "memory_type": "fact",
            "metadata": {},
            "score": 0.8,
            "chat_id": "user1",
            "created_at": row1_created,
        },
        {
            "id": 2,
            "content": "old content",
            "memory_type": "fact",
            "metadata": {},
            "score": 0.9,  # similar semántica mayor, pero decay debería bajarlo
            "chat_id": "user1",
            "created_at": row2_created,
        },
    ]

    decayed = hybrid._apply_time_decay(results)

    # score 2: 0.9 * e^(-0.01 * 100) = 0.9 * e^(-1) = 0.9 * 0.3678 = 0.331
    # score 1: 0.8 * e^(-0.01 * 1) = 0.8 * e^(-0.01) = 0.8 * 0.99 = 0.792
    assert decayed[0]["id"] == 1  # Recent one must win after decay
    assert decayed[0]["score"] > 0.75
    assert decayed[1]["score"] < 0.4
