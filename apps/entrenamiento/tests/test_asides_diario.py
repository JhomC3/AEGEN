"""Spec 022 T6: asides Diario con títulos/separadores índice (RF-6, RF-4)."""

import pathlib

from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token

CSS = pathlib.Path(__file__).resolve().parent.parent / "static" / "css" / "diario.css"


def _client() -> TestClient:
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def test_diario_plantillas_acciones_intactas(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db = str(tmp_path / "gym22d.db")
    init_db(db)
    insert_exercise(db, "Press", "Pectoral", "EMPUJE")
    monkeypatch.setattr(web_context, "DB_PATH", db)
    body = _client().get("/diario", params={"fecha": "2026-08-20"}).text
    assert 'id="plantillas-section"' in body
    assert 'id="nutrition-templates-section"' in body
    assert "apply-template" in body or "Entrenamientos" in body
    assert "apply-meal-template" in body or "Plantillas alimentación" in body


def test_diario_css_lenguaje_indice_con_tokens() -> None:
    css = CSS.read_text()
    assert "#daily-page .splits-catalog-col .panel-title" in css
    assert ".pt-card" in css and "border-bottom" in css
    for token in ("--t-detail-white", "--t-tracking-lg", "--t-surfaces-neutral-700"):
        assert token in css
