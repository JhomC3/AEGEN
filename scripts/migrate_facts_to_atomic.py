# scripts/migrate_facts_to_atomic.py
import asyncio
import json
import logging
import sys
from pathlib import Path

# Configurar path para imports locales
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.knowledge_base import knowledge_base_manager
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_facts_to_atomic")


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

    # Query: buscar memorias activas de tipo 'fact' que NO tengan el campo 'fact_key' en su metadata
    # (lo que indica que son blobs JSON legacy completos en lugar de hechos individuales atómicos)
    sql_find = (
        "SELECT id, chat_id, content FROM memories "
        "WHERE memory_type = 'fact' AND is_active = 1 AND metadata NOT LIKE '%\"fact_key\"%'"
    )

    migrated_count = 0
    atomic_created_count = 0

    try:
        async with db.execute(sql_find) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                logger.info(
                    "No se encontraron registros de hechos legacy para migrar. Esquema limpio."
                )
                return

            logger.info(
                f"Encontrados {len(rows)} registros de hechos legacy para procesar."
            )

            for row in rows:
                legacy_id = row[0]
                chat_id = row[1]
                content = row[2]

                try:
                    # Intentar parsear el JSON legacy
                    legacy_kb = json.loads(content)
                    if not isinstance(legacy_kb, dict):
                        logger.warning(
                            f"Registro legacy {legacy_id} no contiene un diccionario válido. Saltando."
                        )
                        continue

                    # 1. Guardar de forma atómica usando la nueva lógica
                    # Esto itera entities, preferences, etc. y genera registros atómicos
                    logger.info(
                        f"Migrando hechos para el chat {chat_id} (Registro legacy id: {legacy_id})"
                    )
                    await knowledge_base_manager.save_knowledge(chat_id, legacy_kb)

                    # Contabilizar de forma aproximada los hechos creados
                    sections = [
                        "entities",
                        "preferences",
                        "medical",
                        "relationships",
                        "milestones",
                    ]
                    added_atoms = sum(len(legacy_kb.get(s, [])) for s in sections)
                    if "user_name" in legacy_kb:
                        added_atoms += 1

                    atomic_created_count += added_atoms

                    # 2. Desactivar (Soft-delete) el registro legacy original
                    await db.execute(
                        "UPDATE memories SET is_active = 0 WHERE id = ?", (legacy_id,)
                    )
                    await db.commit()

                    logger.info(
                        f"Registro legacy {legacy_id} desactivado correctamente."
                    )
                    migrated_count += 1

                except Exception as ex:
                    logger.error(f"Error procesando registro legacy {legacy_id}: {ex}")
                    continue

        logger.info(
            f"Migración completada exitosamente. "
            f"Procesados: {migrated_count} registros legacy. "
            f"Nuevos hechos atómicos insertados: {atomic_created_count}."
        )

    except Exception as e:
        logger.error(f"Fallo catastrófico en la migración de hechos: {e}")
    finally:
        if should_disconnect:
            await store.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate_legacy_facts())
