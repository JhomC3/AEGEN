import logging
from typing import Any

from src.core.dependencies import get_sqlite_store

logger = logging.getLogger(__name__)


class OutboxManager:
    """Gestiona el encolado y despacho de mensajes asíncronos proactivos."""

    async def schedule_message(
        self, chat_id: str, intent: str, delay_seconds: int
    ) -> int:
        """Programa un mensaje para ser enviado en el futuro."""
        store = get_sqlite_store()
        db = await store.get_db()
        sql = """
            INSERT INTO outbox_messages (chat_id, intent, scheduled_for)
            VALUES (?, ?, datetime('now', ? || ' seconds'))
        """
        async with db.execute(sql, (chat_id, intent, delay_seconds)) as cursor:
            await db.commit()
            return cursor.lastrowid or 0

    async def get_pending_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recupera los mensajes que ya deben enviarse y los bloquea."""
        store = get_sqlite_store()
        db = await store.get_db()

        # En SQLite no hay SELECT FOR UPDATE fácil sin transacciones complejas,
        # pero con 1 worker esto es seguro.
        # Seleccionamos pendientes.
        sql_select = """
            SELECT * FROM outbox_messages
            WHERE status = 'pending' AND scheduled_for <= datetime('now')
            ORDER BY scheduled_for ASC LIMIT ?
        """

        async with db.execute(sql_select, (limit,)) as cursor:
            rows = await cursor.fetchall()
            messages = [dict(r) for r in rows]

        if messages:
            ids = [m["id"] for m in messages]
            marks = ",".join(["?"] * len(ids))
            sql_update = (
                "UPDATE outbox_messages SET status = 'processing' "  # noqa: S608
                f"WHERE id IN ({marks})"  # noqa
            )
            await db.execute(sql_update, ids)
            await db.commit()

        return messages

    async def mark_as_sent(self, message_id: int) -> None:
        """Marca un mensaje como enviado."""
        store = get_sqlite_store()
        db = await store.get_db()
        sql = "UPDATE outbox_messages SET status = 'sent' WHERE id = ?"
        await db.execute(sql, (message_id,))
        await db.commit()

    async def get_and_clear_pending_intents(self, chat_id: str) -> list[str]:
        """Extrae intenciones pendientes y las cancela (Soft Intent Injection)."""
        store = get_sqlite_store()
        db = await store.get_db()

        # Recuperar intenciones
        sql_select = """
            SELECT intent FROM outbox_messages
            WHERE chat_id = ? AND status IN ('pending', 'processing')
        """
        async with db.execute(sql_select, (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            intents = [r["intent"] for r in rows]

        if intents:
            # Cancelarlas para que no se envíen solas
            sql_update = (
                "UPDATE outbox_messages SET status = 'cancelled' "
                "WHERE chat_id = ? AND status IN ('pending', 'processing')"
            )
            await db.execute(sql_update, (chat_id,))
            await db.commit()
            logger.info(f"Extraídas {len(intents)} intenciones pendientes en {chat_id}")

        return intents


outbox_manager = OutboxManager()
