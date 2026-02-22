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
    ("confirmed_at", "TEXT"),
    ("is_active", "INTEGER NOT NULL DEFAULT 1"),
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
