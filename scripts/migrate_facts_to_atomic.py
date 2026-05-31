# scripts/migrate_facts_to_atomic.py
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

    from src.memory.knowledge_base import KnowledgeBaseManager

# Configurar path para imports locales
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_facts_to_atomic")


async def _migrate_single_row(
    row: Any, db: aiosqlite.Connection, kbm: KnowledgeBaseManager
) -> tuple[int, int] | None:
    """Procesa un registro legacy y retorna (migrated, atoms_created) o None."""
    from src.memory.json_sanitizer import safe_json_loads

    legacy_id = row[0]
    chat_id = row[1]
    content = row[2]

    try:
        legacy_kb = safe_json_loads(content)
        if legacy_kb is None:
            logger.warning(
                "Registro legacy %s: JSON irrecuperable. Saltando.", legacy_id
            )
            return None
        if not isinstance(legacy_kb, dict):
            logger.warning(
                "Registro legacy %s no contiene un dict. Saltando.", legacy_id
            )
            return None

        logger.info("Migrando hechos para chat %s (legacy id: %s)", chat_id, legacy_id)
        await kbm.save_knowledge(chat_id, legacy_kb)

        sections = ["entities", "preferences", "medical", "relationships", "milestones"]
        added = sum(len(legacy_kb.get(s, [])) for s in sections)
        if "user_name" in legacy_kb:
            added += 1

        await db.execute("UPDATE memories SET is_active = 0 WHERE id = ?", (legacy_id,))
        await db.commit()

        logger.info("Registro legacy %s desactivado correctamente.", legacy_id)
        return (1, added)
    except Exception as ex:
        logger.error("Error procesando registro legacy %s: %s", legacy_id, ex)
        return None


async def migrate_legacy_facts(store: SQLiteStore | None = None) -> None:
    """
    Escanea la base de datos de SQLite en busca de facts legacy (blobs JSON)
    y los migra a hechos atómicos individuales de forma segura e idempotente.
    """
    db_path = settings.SQLITE_DB_PATH
    if store is None:
        if not Path(db_path).exists():
            logger.warning(
                f"La base de datos en '{db_path}' no existe. Saltando migración."
            )
            return
        store = SQLiteStore(db_path)
        await store.connect()
        should_disconnect = True
    else:
        should_disconnect = False

    logger.info("Iniciando migración de hechos a formato atómico...")
    db = await store.get_db()

    # Buscar facts sin 'fact_key' en metadata (blobs JSON legacy)
    sql_find = (
        "SELECT id, chat_id, content FROM memories "
        "WHERE memory_type = 'fact' AND is_active = 1 "
        "AND metadata NOT LIKE '%\"fact_key\"%'"
    )

    migrated_count = 0
    atomic_created_count = 0

    try:
        async with db.execute(sql_find) as cursor:
            rows = list(await cursor.fetchall())
            if not rows:
                logger.info("No se encontraron hechos legacy. Esquema limpio.")
                return

            logger.info("Encontrados %s registros legacy para procesar.", len(rows))

            for row in rows:
                result = await _migrate_single_row(row, db, knowledge_base_manager)
                if result:
                    migrated_count += result[0]
                    atomic_created_count += result[1]

        logger.info(
            "Migración completada exitosamente. "
            "Procesados: %s registros legacy. "
            "Nuevos hechos atómicos insertados: %s.",
            migrated_count,
            atomic_created_count,
        )

    except Exception as e:
        logger.error(f"Fallo catastrófico en la migración de hechos: {e}")
    finally:
        if should_disconnect:
            await store.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate_legacy_facts())
