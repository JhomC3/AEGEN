"""v022 — bitácora de reportes de sincronización (seguimiento en servidor).

Tabla append-only `sync_reports`: el móvil envía su resumen de sync
(POST /sync/report) y el servidor lo guarda para diagnosticar sin mirar
el teléfono. Sin undo (append-only, como breathing_sessions).
"""

VERSION = 22
NAME = "sync_reports"


def migrate(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_reports (
          id INTEGER PRIMARY KEY,
          device_id TEXT NOT NULL,
          received_at TEXT NOT NULL,
          types_synced INTEGER NOT NULL DEFAULT 0 CHECK (types_synced >= 0),
          delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered >= 0),
          failed INTEGER NOT NULL DEFAULT 0 CHECK (failed >= 0),
          quarantined INTEGER NOT NULL DEFAULT 0 CHECK (quarantined >= 0),
          quarantine_by_type_json TEXT NOT NULL DEFAULT '{}',
          quarantine_sample TEXT NULL,
          notice TEXT NULL,
          permanent_error TEXT NULL,
          nutrition_published INTEGER NOT NULL DEFAULT 0 CHECK (nutrition_published >= 0),
          nutrition_failed INTEGER NOT NULL DEFAULT 0 CHECK (nutrition_failed >= 0)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_reports_received ON sync_reports (received_at DESC)"
    )
