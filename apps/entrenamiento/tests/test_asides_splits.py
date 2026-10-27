"""Spec 022 T4: catálogo de Splits sin <details> (falla antes de migrar)."""

from fastapi.testclient import TestClient

import app as appmod
from src import web_context
from src.database import init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token


def _client() -> TestClient:
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db = str(tmp_path / "gym22s.db")
    init_db(db)
    insert_exercise(db, "Press", "Pectoral", "EMPUJE")
    return db


def test_splits_catalogo_sin_details(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(web_context, "DB_PATH", _db(tmp_path))
    body = _client().get("/splits").text
    catalog = body.split('id="splits-catalog"')[1].split('id="split-catalog-empty"')[0]
    assert "<details" not in catalog
    assert "<summary" not in catalog
    assert "indice-grupo" in catalog
    assert "indice-titulo" in catalog
    assert "indice-fila" in catalog
    assert 'data-action="split-add-item"' in catalog
    assert "data-catalog-list" in catalog
    assert 'id="split-catalog-search"' in body
    assert 'id="split-catalog-empty"' in body
