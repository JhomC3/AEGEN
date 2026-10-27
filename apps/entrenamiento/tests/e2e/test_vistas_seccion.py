"""Spec 042 T2 / Spec 043 T3: columnas por secciones y revert a apilado."""

import sqlite3

from playwright.sync_api import expect


def _seed(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios (grupo_muscular, ejercicio, categoria, origen)"
            " VALUES ('Pectoral', 'Press', 'EMPUJE', 'manual')"
        )
        conn.execute(
            "INSERT INTO training_sets (semana, dia, fecha, set_orden, ejercicio,"
            " reps, kg, rir) VALUES (10, 'JUEVES', '2026-08-20', 1, 'Press', 8, 80, 1)"
        )
        for nombre in ("Split A", "Split B"):
            cur = conn.execute(
                "INSERT INTO training_splits (nombre, created_at, updated_at, activo)"
                " VALUES (?, '2026-08-20 10:00:00', '2026-08-20 10:00:00', 0)",
                (nombre,),
            )
            sid = cur.lastrowid
            conn.execute(
                "INSERT INTO training_split_items (split_id, dia, orden, item_type,"
                " ejercicio, grupo_muscular) VALUES (?, 'LUNES', 1, 'ejercicio',"
                " 'Press', 'Pectoral')",
                (sid,),
            )
        conn.commit()
    finally:
        conn.close()


def _encaja(page):
    m = page.evaluate(
        "() => ({sh: document.scrollingElement.scrollHeight, ih: window.innerHeight})"
    )
    assert m["sh"] <= m["ih"] + 2, m
    assert m["sh"] >= m["ih"] - 60, m


def test_rumbo_apilado_encaja(page, server, server_db_path):
    _seed(server_db_path)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_timeout(400)
    assert page.locator('#rumbo-vistas [role="tab"]').count() == 0
    for panel in ("#rumbo-anual", "#rumbo-semana", "#rumbo-hoy", "#rumbo-yo"):
        expect(page.locator(panel)).to_be_visible()
    _encaja(page)


def test_splits_solo_un_abierto(page, server, server_db_path):
    _seed(server_db_path)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server + "/splits")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    summaries = page.locator(".split-accordion-item details.split-accordion > summary")
    assert summaries.count() >= 2
    summaries.nth(0).click()
    summaries.nth(1).click()
    page.wait_for_timeout(300)
    abiertos = page.locator(".split-accordion-item details.split-accordion[open]")
    assert abiertos.count() == 1
    _encaja(page)


def test_diario_vistas_encajan(page, server, server_db_path):
    _seed(server_db_path)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server + "/diario?fecha=2026-08-20&vista=entrenamiento")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_timeout(400)
    _encaja(page)
    page.locator("#daily-tab-alimentacion").click()
    page.wait_for_timeout(400)
    _encaja(page)
