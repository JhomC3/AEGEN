# src/memory/migration.py
"""
Migraciones de base de datos idempotentes para el esquema de memoria AEGEN.

Maneja la adición de nuevas columnas a bases de datos existentes sin pérdida de datos.
Las nuevas bases de datos obtienen el esquema completo a través de schema.sql;
este módulo cierra la brecha para las bases de datos creadas anteriormente.
"""

from __future__ import annotations

import logging

from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

# Columns to add with their SQL type and default
_PROVENANCE_COLUMNS: list[tuple[str, str]] = [
    ("source_type", "TEXT NOT NULL DEFAULT 'explicit'"),
    ("confidence", "REAL NOT NULL DEFAULT 1.0"),
    ("sensitivity", "TEXT NOT NULL DEFAULT 'low'"),
    ("evidence", "TEXT"),
    ("source_skill", "TEXT"),
    ("confirmed_at", "TEXT"),
    ("is_active", "INTEGER NOT NULL DEFAULT 1"),
    ("parent_id", "INTEGER REFERENCES memories(id) ON DELETE CASCADE"),
]

_INDEXES: list[tuple[str, str]] = [
    (
        "idx_memories_chat_namespace",
        (
            "CREATE INDEX IF NOT EXISTS idx_memories_chat_namespace "
            "ON memories(chat_id, namespace)"
        ),
    ),
    (
        "idx_memories_active",
        (
            "CREATE INDEX IF NOT EXISTS idx_memories_active "
            "ON memories(is_active) WHERE is_active = 1"
        ),
    ),
    (
        "idx_embedding_cache_hash",
        (
            "CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash "
            "ON embedding_cache(content_hash)"
        ),
    ),
    (
        "idx_memories_parent",
        (
            "CREATE INDEX IF NOT EXISTS idx_memories_parent "
            "ON memories(parent_id) WHERE parent_id IS NOT NULL"
        ),
    ),
]


async def _get_existing_columns(store: SQLiteStore) -> set[str]:
    """Retorna el conjunto de nombres de columnas en la tabla memories."""
    db = await store.get_db()
    cursor = await db.execute("PRAGMA table_info(memories)")
    rows = await cursor.fetchall()
    return {row[1] for row in rows}


async def apply_migrations(store: SQLiteStore) -> None:
    """
    Aplica todas las migraciones pendientes de forma idempotente.

    Seguro de llamar en cada arranque: omite columnas/índices que ya existen.
    """
    db = await store.get_db()
    existing = await _get_existing_columns(store)
    applied_cols = 0

    # 1. Add missing columns first
    for col_name, col_def in _PROVENANCE_COLUMNS:
        if col_name not in existing:
            sql = f"ALTER TABLE memories ADD COLUMN {col_name} {col_def}"
            await db.execute(sql)
            applied_cols += 1
            logger.info(f"Migration: added column '{col_name}' to memories")

    if applied_cols > 0:
        await db.commit()
        logger.info(f"Migration: {applied_cols} columns added successfully")

    # 1.5 Crear tabla de aristas transversales (memory_edges) si no existe (ADR-0033)
    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_edges (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                origen_id     INTEGER NOT NULL
                    REFERENCES memories(id) ON DELETE CASCADE,
                destino_id    INTEGER NOT NULL
                    REFERENCES memories(id) ON DELETE CASCADE,
                tipo_relacion TEXT NOT NULL CHECK(tipo_relacion IN (
                    'correlaciona_con', 'causa', 'resuelve',
                    'contradice', 'refuerza'
                )),
                peso          REAL NOT NULL DEFAULT 1.0
                    CHECK(peso >= 0.0 AND peso <= 1.0),
                evidencia     TEXT,
                created_by    TEXT NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_edges_origen ON memory_edges(origen_id);"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_edges_destino ON memory_edges(destino_id);"
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair "
            "ON memory_edges(origen_id, destino_id, tipo_relacion);"
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Error al verificar/crear tabla memory_edges: {e}")

    # 2. Add indexes once columns are guaranteed to exist
    applied_idx = 0
    for _idx_name, idx_sql in _INDEXES:
        try:
            await db.execute(idx_sql)
            applied_idx += 1
        except Exception as e:
            logger.warning(f"Could not create index (may already exist or error): {e}")

    if applied_idx > 0:
        await db.commit()
        logger.info("Migration: index check complete")

    if applied_cols == 0 and applied_idx == 0:
        logger.debug("Migration: schema already up to date")

    # 3. Crear tabla knowledge_files si no existe (gestión de conocimiento)
    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'ingesting', 'done', 'failed')),
                chunker TEXT NOT NULL DEFAULT 'semantic'
                    CHECK(chunker IN ('semantic', 'recursive')),
                chunks_count INTEGER DEFAULT 0,
                chunks_ids TEXT DEFAULT '[]',
                ingested_at TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT
            );
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_files_hash "
            "ON knowledge_files(file_hash)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_files_status "
            "ON knowledge_files(status)"
        )
        await db.commit()
        logger.info("Migration: knowledge_files table check complete")
    except Exception as e:
        logger.warning(f"Error al verificar/crear tabla knowledge_files: {e}")
