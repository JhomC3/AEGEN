"""v023 — Rumbo simple: identidad (1 fila) y día (fecha + 3 valores 1–10).

Reinicio mínimo tras descartar los prototipos HUD/arcade (nunca mergeados):
dos tablas, score siempre derivado (`t1+t2+t3`), sin estado de juego.
"""

VERSION = 23
NAME = "rumbo_simple"


def migrate(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rumbo_yo (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          quien_soy TEXT NOT NULL DEFAULT '',
          quien_no TEXT NOT NULL DEFAULT '',
          construyendo TEXT NOT NULL DEFAULT '',
          t1_nombre TEXT NOT NULL DEFAULT 'Tarea 1',
          t2_nombre TEXT NOT NULL DEFAULT 'Tarea 2',
          t3_nombre TEXT NOT NULL DEFAULT 'Tarea 3',
          updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rumbo_dia (
          fecha TEXT PRIMARY KEY,
          t1 INTEGER NOT NULL CHECK (t1 BETWEEN 1 AND 10),
          t2 INTEGER NOT NULL CHECK (t2 BETWEEN 1 AND 10),
          t3 INTEGER NOT NULL CHECK (t3 BETWEEN 1 AND 10),
          updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
