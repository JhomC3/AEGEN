"""Spec 020 T1: catálogo de métricas reutiliza df inyectado (RF-2, sin cambio visual)."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.health_panels import build_metrics_catalog, build_metrics_index

TZ = "2026-08-10 12:00:00"


def _ts(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def _db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "t20.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE health_records (
            hc_id TEXT PRIMARY KEY, record_type TEXT NOT NULL,
            start_epoch_ms INTEGER NOT NULL, end_epoch_ms INTEGER,
            last_modified_epoch_ms INTEGER NOT NULL, data_origin_package TEXT,
            payload_schema_version INTEGER NOT NULL, value_json TEXT NOT NULL,
            device_id TEXT NOT NULL DEFAULT '', received_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, deleted_at TEXT
        );
        CREATE TABLE parametros_diarios (
            fecha TEXT PRIMARY KEY, peso_kg REAL NOT NULL DEFAULT 70,
            factor_proteina REAL NOT NULL DEFAULT 1.5,
            factor_grasa REAL NOT NULL DEFAULT 1.1,
            kcal_objetivo REAL NOT NULL DEFAULT 2300
        );
        CREATE TABLE diario_alimentacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL,
            orden INTEGER NOT NULL, alimento TEXT NOT NULL, cantidad_g REAL,
            kcal REAL NOT NULL, carbohidratos REAL NOT NULL, fibra REAL NOT NULL,
            proteina REAL NOT NULL, grasa REAL NOT NULL, hierro REAL NOT NULL,
            calcio REAL NOT NULL, vitamina_c REAL NOT NULL, vitamina_a REAL NOT NULL,
            origen TEXT NOT NULL DEFAULT 'google'
        );
        CREATE TABLE training_sets (
            id INTEGER PRIMARY KEY, semana INTEGER NOT NULL, dia TEXT NOT NULL,
            fecha TEXT, set_orden INTEGER NOT NULL, ejercicio TEXT NOT NULL,
            reps REAL, kg REAL, rir REAL, descanso_seg REAL,
            origen TEXT NOT NULL DEFAULT 'google'
        );
        """
    )
    payload = json.dumps({"value": {"count": 5000}})
    conn.execute(
        "INSERT INTO health_records (hc_id, record_type, start_epoch_ms, end_epoch_ms, "
        "last_modified_epoch_ms, payload_schema_version, value_json, received_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
        (
            "s1",
            "STEPS_H1",
            _ts("2026-08-10 09:00"),
            _ts("2026-08-10 09:00"),
            _ts("2026-08-10 09:00"),
            payload,
            TZ,
            TZ,
        ),
    )
    conn.commit()
    conn.close()
    return db_path


def test_catalog_with_injected_df_matches(tmp_path) -> None:
    db_path = _db(tmp_path)
    sel = ("steps",)
    expected = build_metrics_catalog(db_path, sel)
    df = build_metrics_index(db_path, "day")
    got = build_metrics_catalog(db_path, sel, df)
    assert got == expected
