"""POST /sync/report: bitácora del resumen de sync (seguimiento en servidor)."""

import sqlite3

from fastapi.testclient import TestClient

import app as appmod
from src import http_shared, web_context
from src.database import init_db, insert_exercise
from src.security import get_csrf_secret, make_csrf_token

REPORT_URL = "/sync/report"


def _client():
    return TestClient(appmod.app, headers={"X-CSRF-Token": make_csrf_token(get_csrf_secret())})


def _setup_db(tmp_path):
    db = str(tmp_path / "gym.db")
    init_db(db)
    insert_exercise(db, "Press", "Pectoral", "EMPUJE")
    return db


def _body(**over):
    base = {
        "schema_version": 1,
        "device_id": "android-test",
        "types_synced": 29,
        "delivered": 633,
        "failed": 0,
        "quarantined": 3072,
        "quarantine_by_type": {"HEART_RATE_VARIABILITY_RMSSD": 3072},
        "quarantine_sample": "record_type fuera de allow-list",
    }
    base.update(over)
    return base


def test_report_503_when_not_configured(tmp_path, monkeypatch):
    _setup_db(tmp_path)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", "")
    r = _client().post(REPORT_URL, json=_body(), headers={"X-Sync-Token": "x"})
    assert r.status_code == 503


def test_report_401_with_wrong_token(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", "secret")
    r = _client().post(REPORT_URL, json=_body(), headers={"X-Sync-Token": "wrong"})
    assert r.status_code == 401


def test_report_400_with_bad_body(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", "secret")
    bad = _body(delivered=-1)
    r = _client().post(REPORT_URL, json=bad, headers={"X-Sync-Token": "secret"})
    assert r.status_code == 400


def test_report_200_persists_row(tmp_path, monkeypatch):
    db = _setup_db(tmp_path)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", "secret")
    r = _client().post(REPORT_URL, json=_body(), headers={"X-Sync-Token": "secret"})
    assert r.status_code == 200
    assert r.json()["saved"] is True
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT device_id, delivered, quarantined, quarantine_by_type_json "
        "FROM sync_reports ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row[0] == "android-test"
    assert row[1] == 633
    assert row[2] == 3072
    assert "HEART_RATE_VARIABILITY_RMSSD" in row[3]
