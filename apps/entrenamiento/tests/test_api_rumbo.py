"""API v1 JSON de Rumbo simple (aditiva, fusión SDD 001).

Espejo de ui_rumbo.py: validación, servicios y undo. Los POST sin cabecera
CSRF que pasan demuestran la exención exacta.
"""

from fastapi.testclient import TestClient

import app as appmod
from src import http_shared, web_context
from src.database import init_db

SYNC_TOKEN = "secret-rumbo-api"


def _client():
    return TestClient(appmod.app)


def _auth(monkeypatch, tmp_path, token=SYNC_TOKEN):
    db = str(tmp_path / "rumbo_api.db")
    init_db(db)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", token)
    return db


def _h(token=SYNC_TOKEN):
    return {"X-Sync-Token": token}


def test_rumbo_dia_sin_token_401(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    r = _client().get("/api/v1/rumbo/dia?fecha=2026-10-04")
    assert r.status_code == 401


def test_rumbo_dia_vacio_y_guardado(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    r = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h())
    assert r.status_code == 200
    assert r.json()["dia"] is None
    r = c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": "2026-10-04", "t1": 8, "t2": 7, "t3": 9},
    )
    assert r.status_code == 200
    assert r.json()["score"] == 24
    r = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h())
    assert r.json()["dia"]["t1"] == 8


def test_rumbo_dia_invalido_400_sin_escritura(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    r = c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": "2026-10-04", "t1": 99, "t2": 7, "t3": 9},
    )
    assert r.status_code == 400
    r = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h())
    assert r.json()["dia"] is None


def test_rumbo_preguntas_y_respuesta_con_undo(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    r = c.get("/api/v1/rumbo/preguntas", headers=_h())
    assert r.status_code == 200
    assert r.json()["count"] > 0
    r = c.post(
        "/api/v1/rumbo/respuesta",
        headers=_h(),
        json={"pregunta": "ex01", "respuesta": "Prueba API"},
    )
    assert r.status_code == 200
    r = c.get("/api/v1/rumbo/respuestas?pregunta=ex01", headers=_h())
    assert r.json()["vigente"]["respuesta"] == "Prueba API"
    assert c.get("/api/v1/undo/peek", headers=_h()).json()["kind"] == "rumbo"
    r = c.post("/api/v1/undo", headers=_h())
    assert r.json()["kind"] == "rumbo"
    r = c.get("/api/v1/rumbo/respuestas?pregunta=ex01", headers=_h())
    assert r.json()["vigente"]["respuesta"] != "Prueba API"


def test_rumbo_respuestas_sin_pregunta_400(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    r = _client().get("/api/v1/rumbo/respuestas", headers=_h())
    assert r.status_code == 400
