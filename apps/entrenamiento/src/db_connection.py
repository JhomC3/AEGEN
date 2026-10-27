"""Configured SQLite connection factory and context managers."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

BUSY_TIMEOUT_MS = 5000


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def read_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect_db(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(db_path: str, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Transacción SQLite; con `immediate=True` reserva el bloqueo de escritura
    al empezar (BEGIN IMMEDIATE) para que comprobar-y-escribir sea atómico."""
    conn = connect_db(db_path)
    try:
        if immediate:
            conn.execute("BEGIN IMMEDIATE")
        with conn:
            yield conn
    finally:
        conn.close()


@contextmanager
def _use_conn(
    db_path: str, conn: sqlite3.Connection | None, immediate: bool = False
) -> Iterator[sqlite3.Connection]:
    """Reutiliza `conn` si se aporta (misma transacción) o abre una propia.

    Permite que verificar, mutar y registrar journal compartan una única
    transacción sin duplicar el SQL.
    """
    if conn is not None:
        yield conn
    else:
        with transaction(db_path, immediate=immediate) as fresh:
            yield fresh
