import asyncio
import contextlib
import logging

from src.agents.specialists.life_reviewer import life_reviewer
from src.core.dependencies import get_sqlite_store

logger = logging.getLogger(__name__)


class LifeReviewerWorker:
    """Worker de análisis longitudinal periódico."""

    def __init__(self, interval_hours: int = 24) -> None:
        self.interval_hours = interval_hours
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"LifeReviewerWorker ok ({self.interval_hours}h)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("LifeReviewerWorker detenido")

    async def _loop(self) -> None:
        while self._running:
            try:
                logger.info("Iniciando revisión de vida...")
                store = get_sqlite_store()
                db = await store.get_db()

                sql = (
                    "SELECT DISTINCT chat_id FROM user_milestones "
                    "WHERE created_at >= datetime('now', '-30 days')"
                )
                async with db.execute(sql) as cursor:
                    rows = await cursor.fetchall()
                    chat_ids = [r["chat_id"] for r in rows]

                for chat_id in chat_ids:
                    await life_reviewer.review_user_progress(chat_id)
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error LifeReviewerWorker: {e}")

            await asyncio.sleep(self.interval_hours * 3600)


life_reviewer_worker = LifeReviewerWorker()
