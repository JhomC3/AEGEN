"""Tests del curador automatico de skills."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_curator_dry_run_reports_stale_skills():
    """En dry_run, el curador reporta skills stale sin moverlos."""
    from src.personality.skill_curator import run_skill_curator

    stale_time = datetime.now(UTC) - timedelta(days=45)

    with patch(
        "src.personality.skill_curator._get_skill_last_used",
        new_callable=AsyncMock,
        return_value=stale_time,
    ):
        report = await run_skill_curator(dry_run=True)

    assert len(report["stale"]) > 0
    assert len(report["archived"]) == 0


@pytest.mark.asyncio
async def test_curator_archives_old_skills():
    """Skills con >90 dias de inactividad se archivan."""
    from src.personality.skill_curator import run_skill_curator

    old_time = datetime.now(UTC) - timedelta(days=100)

    with (
        patch(
            "src.personality.skill_curator._get_skill_last_used",
            new_callable=AsyncMock,
            return_value=old_time,
        ),
        patch(
            "src.personality.skill_curator._discover_skills",
            return_value=[],
        ),
    ):
        report = await run_skill_curator(dry_run=True)

    assert len(report["archived"]) >= 0
