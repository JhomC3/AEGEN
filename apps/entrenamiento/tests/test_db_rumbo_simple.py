"""Esquema Rumbo simple: tablas v023/v024 (specs 019/020)."""

import sqlite3

from src.database import init_db


def test_v023_creates_rumbo_simple_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    yo_cols = {r[1] for r in conn.execute("PRAGMA table_info(rumbo_yo)")}
    dia_cols = {r[1] for r in conn.execute("PRAGMA table_info(rumbo_dia)")}
    conn.close()
    assert {"rumbo_yo", "rumbo_dia"} <= tables
    assert {
        "quien_soy",
        "quien_no",
        "construyendo",
        "t1_nombre",
        "t2_nombre",
        "t3_nombre",
    } <= yo_cols
    assert {"fecha", "t1", "t2", "t3"} <= dia_cols


def test_v024_creates_rumbo_respuestas_table(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rumbo_respuestas)")}
    count = conn.execute("SELECT COUNT(*) FROM rumbo_respuestas").fetchone()[0]
    conn.close()
    assert {"pregunta", "respuesta", "origen", "created_at"} <= cols
    assert count == 36
