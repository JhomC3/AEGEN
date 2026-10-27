"""Spec 022 T2: asides con vocabulario índice (falla antes de migrar)."""

from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token


def _client() -> TestClient:
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db = str(tmp_path / "gym22.db")
    init_db(db)
    insert_exercise(db, "Press", "Pectoral", "EMPUJE")
    return db


def test_dashboard_catalogo_lenguaje_indice(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    body = _client().get("/").text
    assert "indice-grupo" in body
    assert "indice-titulo" in body
    assert "indice-fila" in body
    assert "toggle-group" not in body
    assert 'data-action="toggle-muscle"' in body
    assert "aria-pressed=" in body


def test_metricas_lenguaje_indice_sin_plegado(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    body = _client().get("/").text
    assert "toggle-metric-group" not in body
    assert 'data-action="toggle-metric"' in body
    assert "indice-grupo" in body
