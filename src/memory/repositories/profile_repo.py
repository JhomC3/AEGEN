import json
import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class ProfileRepository:
    """
    Repositorio para operaciones de perfil en SQLite.
    """

    def __init__(self, store: Any):
        self.store = store

    async def get_db(self) -> aiosqlite.Connection:
        return await self.store.get_db()

    async def save_profile(self, chat_id: str, profile_data: dict) -> None:
        """Guarda un perfil de usuario en la DB."""
        db = await self.get_db()
        payload = json.dumps(profile_data, ensure_ascii=False)

        try:
            await db.execute(
                """
                INSERT INTO profiles (chat_id, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chat_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, payload),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Error saving profile to SQLite: {e}")
            await db.rollback()
            raise

    async def load_profile(self, chat_id: str) -> dict | None:
        """Carga un perfil de usuario de la DB."""
        db = await self.get_db()
        try:
            async with db.execute(
                "SELECT data FROM profiles WHERE chat_id = ?", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row["data"])
                return None
        except Exception as e:
            logger.error(f"Error loading profile from SQLite: {e}")
            return None
