"""Spec 039 T2: GET / sirve la selección de la URL en el primer pintado (RF-1)."""

import datetime
import json
import re
import sqlite3
from typing import Any

from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token
from src.training_service import calculate_cycle_week, parse_cycle_start


def _client() -> TestClient:
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db = str(tmp_path / "gym23.db")
    init_db(db)
    insert_exercise(db, "Press", "Pectoral", "EMPUJE")
    insert_exercise(db, "Curl", "Biceps", "TIRON")
    ciclo = parse_cycle_start()
    filas = []
    for i, (f, ej) in enumerate(
        [("2026-08-18", "Press"), ("2026-08-19", "Press"), ("2026-08-20", "Curl")]
    ):
        sem = calculate_cycle_week(datetime.date.fromisoformat(f), ciclo)
        filas.append((sem, "LUNES", f, i + 1, ej, 8.0, 80.0, 1.0))
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


def _app_config(body: str) -> dict[str, Any]:
    m = re.search(
        r'<script id="app-config" type="application/json">(.*?)</script>', body, re.DOTALL
    )
    assert m, "falta #app-config"
    return json.loads(m.group(1))


def test_index_sirve_seleccion_musculo(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    body = _client().get("/", params={"musculos": "Pectoral"}).text
    assert 'data-foco="Pectoral"' in body
    assert body.count('aria-pressed="true"') >= 1
    assert ">Pectoral</button>" in body  # tab del Historial de la selección
    cfg = _app_config(body)
    assert cfg["seleccion_inicial"]["musculos"] == ["Pectoral"]
    assert cfg["seleccion_inicial"]["gran"] == "day"


def test_index_sin_params_es_global(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    body = _client().get("/").text
    cfg = _app_config(body)
    assert cfg["seleccion_inicial"]["musculos"] == []
    assert cfg["seleccion_inicial"]["ejercicios"] == []
    assert ">Global</button>" in body


def test_index_ventana_invalida_400(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    r = _client().get("/", params={"ventana": 9})
    assert r.status_code == 400
