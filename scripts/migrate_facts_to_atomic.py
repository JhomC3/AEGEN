# scripts/migrate_facts_to_atomic.py
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

# Configurar path para imports locales
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.memory.ingestion_pipeline import IngestionPipeline
from src.memory.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_facts_to_atomic")

_DOMAIN_MAP = {
    "presupuesto": "finance",
    "gasto": "finance",
    "ingreso": "finance",
    "entrenamiento": "fitness",
    "sentadilla": "fitness",
    "peso": "fitness",
    "calorias": "nutrition",
    "dieta": "nutrition",
    "estres": "psychology",
    "ansiedad": "psychology",
    "meta": "psychology",
    "user_name": "psychology",
}


def _infer_domain(item: dict) -> str:
    """Infiere el dominio a partir de los campos del item."""
    text = json.dumps(item).lower()
    for keyword, domain in _DOMAIN_MAP.items():
        if keyword in text:
            return domain
    return "general"


async def _migrate_single_row(
    row: Any, db: aiosqlite.Connection, pipeline: IngestionPipeline
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

        # Cada registro legacy es UN solo hecho atomico (dict plano)
        # No es una coleccion con entities/preferences, es el item en si
        fact_key = (
            legacy_kb.get("name")
            or legacy_kb.get("key")
            or legacy_kb.get("type")
            or list(legacy_kb.keys())[0]
            if legacy_kb
            else ""
        )
        text = json.dumps(legacy_kb, ensure_ascii=False)
        meta = {
            "source": "migration",
            "type": "structured_fact",
            "source_type": legacy_kb.get("source_type", "explicit"),
            "confidence": legacy_kb.get("confidence", 1.0),
            "evidence": str(legacy_kb.get("evidence", "")),
            "sensitivity": str(legacy_kb.get("sensitivity", "medium")),
            "domain": _infer_domain(legacy_kb),
            "hierarchy_level": 4,
            "fact_key": str(fact_key),
        }
        await pipeline.process_text(
            chat_id=chat_id,
            text=text,
            memory_type="fact",
            metadata=meta,
            source_skill="knowledge_base",
        )
        added = 1

        await db.execute("UPDATE memories SET is_active = 0 WHERE id = ?", (legacy_id,))
        await db.commit()

        logger.info(
            "Registro legacy %s desactivado (%d hechos atomicos).", legacy_id, added
        )
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

    pipeline = IngestionPipeline(store)

    # Buscar facts sin 'fact_key' en metadata (blobs JSON legacy)
    # No filtramos por is_active para poder reprocesar registros
    # que fueron marcados como inactivos en ejecuciones fallidas previas
    sql_find = (
        "SELECT id, chat_id, content FROM memories "
        "WHERE memory_type = 'fact' "
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
                result = await _migrate_single_row(row, db, pipeline)
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
