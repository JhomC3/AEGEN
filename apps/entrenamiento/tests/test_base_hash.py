"""Precondición atómica `base_hash` (fusión SDD 001, RF-07).

Un `base_hash` viejo ante cambio concurrente responde 409 sin escribir;
con hash vigente escribe 200. Sin `base_hash` se conserva el Last-Write-Wins.
"""

from fastapi.testclient import TestClient

import app as appmod
from src import http_shared, web_context
from src.database import init_db

SYNC_TOKEN = "secret-base-hash"


def _client():
    return TestClient(appmod.app)


def _auth(monkeypatch, tmp_path, token=SYNC_TOKEN):
    db = str(tmp_path / "base_hash.db")
    init_db(db)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", token)
    return db


def _h(token=SYNC_TOKEN):
    return {"X-Sync-Token": token}


def test_sesion_409_ante_cambio_y_200_vigente(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    c.post(
        "/api/v1/ejercicio",
        headers=_h(),
        json={"ejercicio": "Press", "grupo_muscular": "Pectoral"},
    )
    r = c.post(
        "/api/v1/sesion",
        headers=_h(),
        json={
            "fecha": "2026-10-04",
            "sets": [{"ejercicio": "Press", "kg": 60, "reps": 8, "rir": 1}],
        },
    )
    assert r.status_code == 200
    viejo = c.get("/api/v1/sesion?fecha=2026-10-04", headers=_h()).json()["base_hash"]
    c.post(
        "/api/v1/sesion",
        headers=_h(),
        json={
            "fecha": "2026-10-04",
            "sets": [{"ejercicio": "Press", "kg": 70, "reps": 8, "rir": 1}],
        },
    )
    r = c.post(
        "/api/v1/sesion",
        headers=_h(),
        json={
            "fecha": "2026-10-04",
            "sets": [{"ejercicio": "Press", "kg": 80, "reps": 8, "rir": 1}],
            "base_hash": viejo,
        },
    )
    assert r.status_code == 409
    assert "cambió desde la lectura" in r.json()["detail"]
    assert c.get("/api/v1/sesion?fecha=2026-10-04", headers=_h()).json()["sets"][0]["kg"] == 70.0
    vigente = c.get("/api/v1/sesion?fecha=2026-10-04", headers=_h()).json()["base_hash"]
    r = c.post(
        "/api/v1/sesion",
        headers=_h(),
        json={
            "fecha": "2026-10-04",
            "sets": [{"ejercicio": "Press", "kg": 80, "reps": 8, "rir": 1}],
            "base_hash": vigente,
        },
    )
    assert r.status_code == 200
    assert r.json()["sets"][0]["kg"] == 80.0


def test_diario_409_ante_cambio(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    c.post(
        "/api/v1/alimento",
        headers=_h(),
        json={"nombre": "Avena", "categoria": "Cereal", "kcal": 389},
    )
    r = c.post(
        "/api/v1/diario",
        headers=_h(),
        json={"fecha": "2026-10-04", "entradas": [{"alimento": "Avena", "cantidad_g": 30}]},
    )
    assert r.status_code == 200
    viejo = c.get("/api/v1/diario?fecha=2026-10-04", headers=_h()).json()["base_hash"]
    c.post(
        "/api/v1/diario",
        headers=_h(),
        json={"fecha": "2026-10-04", "entradas": [{"alimento": "Avena", "cantidad_g": 20}]},
    )
    r = c.post(
        "/api/v1/diario",
        headers=_h(),
        json={
            "fecha": "2026-10-04",
            "entradas": [{"alimento": "Avena", "cantidad_g": 50}],
            "base_hash": viejo,
        },
    )
    assert r.status_code == 409
    dia = c.get("/api/v1/diario?fecha=2026-10-04", headers=_h()).json()
    assert dia["entradas"][0]["cantidad_g"] == 20.0


def test_rumbo_dia_409_ante_cambio(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    r = c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": "2026-10-04", "t1": 5, "t2": 5, "t3": 5},
    )
    assert r.status_code == 200
    viejo = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["base_hash"]
    c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": "2026-10-04", "t1": 6, "t2": 6, "t3": 6},
    )
    r = c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": "2026-10-04", "t1": 8, "t2": 8, "t3": 8, "base_hash": viejo},
    )
    assert r.status_code == 409
    assert c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"]["t1"] == 6
