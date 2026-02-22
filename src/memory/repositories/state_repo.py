import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class StateRepository:
    """
    Repositorio para gestionar el Estado de Vida (Metas e Hitos) del usuario.
    """

    def __init__(self, store: Any):
        self.store = store

    async def get_db(self) -> aiosqlite.Connection:
        return await self.store.get_db()

    async def add_goal(
        self,
        chat_id: str,
        goal_type: str,
        description: str,
        target_date: str | None = None,
    ) -> int:
        db = await self.get_db()
        sql = """
            INSERT INTO user_goals (chat_id, goal_type, description, target_date)
            VALUES (?, ?, ?, ?)
        """
        async with db.execute(
            sql, (chat_id, goal_type, description, target_date)
        ) as cursor:
            await db.commit()
            return cursor.lastrowid or 0

    async def get_active_goals(self, chat_id: str) -> list[dict[str, Any]]:
        db = await self.get_db()
        sql = "SELECT * FROM user_goals WHERE chat_id = ? AND status = 'active'"
        async with db.execute(sql, (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_goal_status(self, goal_id: int, status: str) -> bool:
        db = await self.get_db()
        sql = "UPDATE user_goals SET status = ? WHERE id = ?"
        async with db.execute(sql, (status, goal_id)) as cursor:
            await db.commit()
            return cursor.rowcount > 0

    async def add_milestone(
        self,
        chat_id: str,
        action: str,
        status: str,
        emotion: str | None = None,
        description: str | None = None,
        goal_id: int | None = None,
    ) -> int:
        db = await self.get_db()
        sql = """
            INSERT INTO user_milestones
                (chat_id, goal_id, action, status, emotion, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        async with db.execute(
            sql, (chat_id, goal_id, action, status, emotion, description)
        ) as cursor:
            await db.commit()
            return cursor.lastrowid or 0

    async def get_recent_milestones(
        self, chat_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        db = await self.get_db()
        sql = """
            SELECT m.*, g.description as goal_description
            FROM user_milestones m
            LEFT JOIN user_goals g ON m.goal_id = g.id
            WHERE m.chat_id = ?
            ORDER BY m.created_at DESC
            LIMIT ?
        """
        async with db.execute(sql, (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
