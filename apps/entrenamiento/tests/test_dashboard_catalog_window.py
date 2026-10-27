"""Spec 020 T3: GET / ordena el catálogo con ventana 8 como /grafica (RF-1)."""

import datetime
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import get_dashboard_catalog, init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token
from src.summary_service import db_window
from src.training_service import calculate_cycle_week, parse_cycle_start


def _client() -> TestClient:
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _seed(tmp_path: Path) -> str:
    db = str(tmp_path / "gym20.db")
    init_db(db)
    insert_exercise(db, "Press A", "Pectoral", "EMPUJE")
    insert_exercise(db, "Press B", "Pectoral", "EMPUJE")
    ciclo = parse_cycle_start()
    filas = []
    for i in range(10):
        f = "2026-01-05"
        sem = calculate_cycle_week(datetime.date.fromisoformat(f), ciclo)
        filas.append((sem, "LUNES", f, i + 1, "Press A", 8.0, 80.0, 1.0))
    for i in range(5):
        f = "2026-08-20"
        sem = calculate_cycle_week(datetime.date.fromisoformat(f), ciclo)
        filas.append((sem, "JUEVES", f, i + 1, "Press B", 8.0, 80.0, 1.0))
    conn = sqlite3.connect(db)
    try:
        conn.executemany(
            "INSERT INTO training_sets (semana,dia,fecha,set_orden,ejercicio,reps,kg,rir)"
            " VALUES (?,?,?,?,?,?,?,?)",
            filas,
        )
        conn.commit()
    finally:
        conn.close()
    return db


def test_index_usa_ventana_8_como_grafica(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = _seed(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    window = db_window(db, 8)
    assert window is not None
    expected = get_dashboard_catalog(db, window.start.isoformat(), window.end.isoformat())
    grupo = next(g for g in expected if g["name"] == "Pectoral")
    assert [e["name"] for e in grupo["exercises"]][:2] == ["Press B", "Press A"]
    body = _client().get("/").text
    pos_b = body.index('data-foco="Press B"')
    pos_a = body.index('data-foco="Press A"')
    assert pos_b < pos_a
