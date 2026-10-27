"""Tests de rutas Rumbo simple: página, mutaciones OOB y undo (spec 019)."""

import datetime

from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import get_rumbo_dia, get_rumbo_yo, init_db
from src.security import get_csrf_secret, make_csrf_token


def _client():
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _setup_db(tmp_path):
    db = str(tmp_path / "gym.db")
    init_db(db)
    return db


def _hoy() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def test_rumbo_pagina_renderiza_secciones(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    body = _client().get("/rumbo").text
    assert 'id="rumbo-yo"' in body
    assert 'id="rumbo-anual"' in body
    assert 'id="rumbo-semana"' in body
    assert 'id="rumbo-hoy"' in body
    assert "Rumbo" in body
    assert 'href="/rumbo"' in _client().get("/").text


def test_rumbo_css_con_digest_versionado(tmp_path, monkeypatch):
    from pathlib import Path

    from src.static_assets import static_digest

    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    body = _client().get("/rumbo").text
    assert f"/static/css/rumbo.css?v={static_digest('css/rumbo.css')}" in body
    root = Path(__file__).resolve().parents[1]
    assert '@import "rumbo.css"' not in (root / "static" / "css" / "app.css").read_text()


def test_rumbo_dia_guarda_y_actualiza_fragmentos(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    hoy = _hoy()
    r = _client().post("/rumbo/dia", data={"fecha": hoy, "t1": "8", "t2": "7", "t3": "9"})
    assert r.status_code == 200
    assert "24/30" in r.text
    assert 'id="rumbo-hoy"' in r.text
    assert 'id="rumbo-semana"' in r.text
    assert 'id="rumbo-anual"' in r.text
    assert get_rumbo_dia(db, hoy) == {"fecha": hoy, "t1": 8, "t2": 7, "t3": 9}
    body = _client().get("/rumbo").text
    assert "24/30" in body
    assert "24/210" in body


def test_rumbo_dia_rechaza_fuera_de_rango(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    r = _client().post("/rumbo/dia", data={"fecha": _hoy(), "t1": "0", "t2": "5", "t3": "5"})
    assert r.status_code == 400
    assert get_rumbo_dia(db, _hoy()) is None


def test_rumbo_yo_guarda_identidad(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    r = _client().post(
        "/rumbo/yo",
        data={
            "fecha": _hoy(),
            "quien_soy": "Soy constante",
            "quien_no": "El que abandona",
            "construyendo": "Mi vida",
            "t1_nombre": "Entrenar",
            "t2_nombre": "Leer",
            "t3_nombre": "Trabajar",
        },
    )
    assert r.status_code == 200
    assert 'id="rumbo-yo"' in r.text
    yo = get_rumbo_yo(db)
    assert yo["quien_soy"] == "Soy constante"
    assert yo["t1_nombre"] == "Entrenar"
    assert "Entrenar" in _client().get("/rumbo").text


def test_rumbo_undo_revierte_dia(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    hoy = _hoy()
    _client().post("/rumbo/dia", data={"fecha": hoy, "t1": "9", "t2": "9", "t3": "9"})
    assert get_rumbo_dia(db, hoy) is not None
    u = _client().post("/undo", data={"fecha": hoy})
    assert u.status_code == 200
    assert get_rumbo_dia(db, hoy) is None
    # Spec 044 H05: sin registro el encabezado dice "Sin registro", no "0/30".
    assert "Sin registro" in _client().get("/rumbo").text


def test_rumbo_pregunta_dialog_muestra_actualizar(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    body = _client().get("/rumbo/pregunta/ex01").text
    assert "insatisfacción" in body
    assert "Guardar" in body
    assert "/rumbo/pregunta/ex02" in body
    assert _client().get("/rumbo/pregunta/no-existe").status_code == 400


def test_rumbo_respuesta_apila_y_actualiza_sidebar(tmp_path, monkeypatch):
    from src.database import get_respuesta_vigente

    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    antes = get_respuesta_vigente(db, "ex01")["respuesta"]
    assert "tolerar" in antes
    r = _client().post(
        "/rumbo/respuesta", data={"pregunta": "ex01", "respuesta": "Mi versión nueva"}
    )
    assert r.status_code == 200
    assert 'id="rumbo-preguntas"' in r.text
    assert get_respuesta_vigente(db, "ex01")["respuesta"] == "Mi versión nueva"
    assert "Mi versión nueva" in _client().get("/rumbo/pregunta/ex01").text
    assert (
        _client().post("/rumbo/respuesta", data={"pregunta": "ex01", "respuesta": "  "}).status_code
        == 400
    )
    assert (
        _client().post("/rumbo/respuesta", data={"pregunta": "xx", "respuesta": "y"}).status_code
        == 400
    )
    u = _client().post("/undo", data={"fecha": _hoy()})
    assert u.status_code == 200
    assert get_respuesta_vigente(db, "ex01")["respuesta"] == antes


def test_rumbo_noscript_honesto_sin_promesa_de_guardado(tmp_path, monkeypatch):
    """H04 (spec 045): el HTML servido declara JS requisito, sin promesas falsas."""
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    body = _client().get("/rumbo").text
    assert "Rumbo necesita JavaScript para guardar" in body
    assert "guardan igual" not in body
