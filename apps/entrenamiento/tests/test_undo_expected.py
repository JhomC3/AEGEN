"""Undo con precondición atómica (fusión SDD 001, RF-07).

La entrada exacta (id+kind del preview) se comprueba y consume en una sola
transacción: otra escritura intermedia (mismo tipo o no) responde 409 intacto.
"""

from fastapi.testclient import TestClient

import app as appmod
from src import http_shared, web_context
from src.database import init_db

SYNC_TOKEN = "secret-undo-expected"


def _client():
    return TestClient(appmod.app)


def _auth(monkeypatch, tmp_path, token=SYNC_TOKEN):
    db = str(tmp_path / "undo_expected.db")
    init_db(db)
    monkeypatch.setattr(web_context, "DB_PATH", db)
    monkeypatch.setattr(http_shared, "HC_SYNC_TOKEN", token)
    return db


def _h(token=SYNC_TOKEN):
    return {"X-Sync-Token": token}


def _dia(c, fecha="2026-10-04", t1=5, t2=5, t3=5):
    return c.post(
        "/api/v1/rumbo/dia",
        headers=_h(),
        json={"fecha": fecha, "t1": t1, "t2": t2, "t3": t3},
    )


def test_undo_expected_409_ante_escritura_intermedia_mismo_tipo(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    assert _dia(c).status_code == 200
    peek1 = c.get("/api/v1/undo/peek", headers=_h()).json()
    assert _dia(c, t1=9, t2=9, t3=9).status_code == 200
    r = c.post(
        "/api/v1/undo",
        headers=_h(),
        json={"expected": {"id": peek1["entry_id"], "kind": "rumbo"}},
    )
    assert r.status_code == 409
    assert "cambió desde el preview" in r.json()["detail"]
    dia = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"]
    assert (dia["t1"], dia["t2"], dia["t3"]) == (9, 9, 9)
    peek2 = c.get("/api/v1/undo/peek", headers=_h()).json()
    assert peek2["entry_id"] != peek1["entry_id"]


def test_undo_expected_exito_y_preciso(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    assert _dia(c).status_code == 200
    peek = c.get("/api/v1/undo/peek", headers=_h()).json()
    r = c.post(
        "/api/v1/undo",
        headers=_h(),
        json={"expected": {"id": peek["entry_id"], "kind": peek["kind"]}},
    )
    assert r.status_code == 200
    assert r.json()["kind"] == "rumbo"
    assert c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"] is None
    assert c.get("/api/v1/undo/peek", headers=_h()).json()["kind"] == "empty"


def test_undo_expected_invalido_400(monkeypatch, tmp_path):
    _auth(monkeypatch, tmp_path)
    c = _client()
    r = c.post("/api/v1/undo", headers=_h(), json={"expected": {"id": "x", "kind": 1}})
    assert r.status_code == 400


def test_undo_expected_escritura_intercalada_durante_restore(tmp_path, monkeypatch):
    """Una escritura concurrente en plena restauración sobrevive (no la borra)
    y queda registrada; el undo consumido es el esperado."""
    import threading

    import src.mutation_service as mut

    _auth(monkeypatch, tmp_path)
    c = _client()
    assert _dia(c).status_code == 200
    peek = c.get("/api/v1/undo/peek", headers=_h()).json()
    started = threading.Event()

    real_restore = mut.restore_rumbo_simple

    def lento(db_path, snapshot, conn=None):
        started.set()
        import time as _time

        _time.sleep(1.0)
        return real_restore(db_path, snapshot, conn=conn)

    monkeypatch.setattr(mut, "restore_rumbo_simple", lento)
    errores = []

    def deshacer():
        try:
            r = c.post(
                "/api/v1/undo",
                headers=_h(),
                json={"expected": {"id": peek["entry_id"], "kind": "rumbo"}},
            )
            errores.append(r.status_code)
        except Exception as exc:  # noqa: BLE001
            errores.append(repr(exc))

    hilo = threading.Thread(target=deshacer)
    hilo.start()
    assert started.wait(timeout=10)
    r2 = _dia(c, t1=9, t2=9, t3=9)
    assert r2.status_code == 200
    hilo.join(timeout=30)
    assert errores == [200]
    dia = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"]
    assert (dia["t1"], dia["t2"], dia["t3"]) == (9, 9, 9)
    top = c.get("/api/v1/undo/peek", headers=_h()).json()
    assert top["kind"] == "rumbo" and top["entry_id"] != peek["entry_id"]
    # Deshacer la escritura intercalada restaura el estado inmediatamente
    # anterior a su ejecución (vacío), sin resucitar el 5/5/5 ya deshecho.
    r = c.post(
        "/api/v1/undo",
        headers=_h(),
        json={"expected": {"id": top["entry_id"], "kind": "rumbo"}},
    )
    assert r.status_code == 200
    assert c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"] is None


def test_undo_expected_fallo_restore_sin_cambios_parciales(tmp_path, monkeypatch):
    """Si el restore falla, la DB y la pila quedan intactas (todo revierte)."""
    import src.mutation_service as mut

    _auth(monkeypatch, tmp_path)
    c = _client()
    assert _dia(c, t1=4, t2=4, t3=4).status_code == 200
    peek = c.get("/api/v1/undo/peek", headers=_h()).json()

    def roto(db_path, snapshot, conn=None):
        raise RuntimeError("restore roto a propósito")

    monkeypatch.setattr(mut, "restore_rumbo_simple", roto)
    r = c.post(
        "/api/v1/undo",
        headers=_h(),
        json={"expected": {"id": peek["entry_id"], "kind": "rumbo"}},
    )
    assert r.status_code == 500
    dia = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"]
    assert (dia["t1"], dia["t2"], dia["t3"]) == (4, 4, 4)
    top = c.get("/api/v1/undo/peek", headers=_h()).json()
    assert top["entry_id"] == peek["entry_id"]


def test_undo_expected_fallo_tras_borrar_revierte_todo(tmp_path, monkeypatch):
    """Si el restore falla DESPUÉS de borrar datos, la transacción revierte:
    filas intactas y la misma entrada sigue en la cima."""
    import src.mutation_service as mut

    _auth(monkeypatch, tmp_path)
    c = _client()
    assert _dia(c, t1=4, t2=4, t3=4).status_code == 200
    peek = c.get("/api/v1/undo/peek", headers=_h()).json()

    def roto_tras_borrar(db_path, snapshot, conn=None):
        assert conn is not None
        conn.execute("DELETE FROM rumbo_dia")
        raise RuntimeError("fallo tras borrar")

    monkeypatch.setattr(mut, "restore_rumbo_simple", roto_tras_borrar)
    r = c.post(
        "/api/v1/undo",
        headers=_h(),
        json={"expected": {"id": peek["entry_id"], "kind": "rumbo"}},
    )
    assert r.status_code == 500
    dia = c.get("/api/v1/rumbo/dia?fecha=2026-10-04", headers=_h()).json()["dia"]
    assert (dia["t1"], dia["t2"], dia["t3"]) == (4, 4, 4)
    top = c.get("/api/v1/undo/peek", headers=_h()).json()
    assert top["entry_id"] == peek["entry_id"]
