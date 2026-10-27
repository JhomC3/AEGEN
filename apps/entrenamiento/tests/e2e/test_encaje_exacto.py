"""Spec 041 T2: encaje exacto de las 4 pestañas (falla antes de acotar)."""

import sqlite3

VIEWPORTS = [(1440, 900), (1280, 1024)]
TABS = ["/", "/diario?fecha=2026-08-20", "/splits", "/rumbo"]


def _seed(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios (grupo_muscular, ejercicio, categoria, origen)"
            " VALUES ('Pectoral', 'Press', 'EMPUJE', 'manual'),"
            " ('Biceps', 'Curl', 'TIRON', 'manual')"
        )
        conn.execute(
            "INSERT INTO training_sets (semana, dia, fecha, set_orden, ejercicio,"
            " reps, kg, rir) VALUES (10, 'JUEVES', '2026-08-20', 1, 'Press', 8, 80, 1),"
            " (10, 'JUEVES', '2026-08-20', 2, 'Press', 8, 80, 1),"
            " (10, 'JUEVES', '2026-08-20', 1, 'Curl', 10, 40, 1)"
        )
        conn.execute(
            "INSERT INTO diario_alimentacion (fecha, orden, alimento, cantidad_g, kcal,"
            " carbohidratos, fibra, proteina, grasa, hierro, calcio, vitamina_c,"
            " vitamina_a, magnesio, zinc, potasio, sodio, vitamina_d, vitamina_e,"
            " vitamina_k, folato, vitamina_b12, vitamina_b6, yodo, selenio)"
            " VALUES ('2026-08-20', 1, 'Avena', 100, 350, 60, 10, 12, 6, 1, 1, 1, 1,"
            " 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)"
        )
        cur = conn.execute(
            "INSERT INTO training_splits (nombre, created_at, updated_at)"
            " VALUES ('Encaje', '2026-08-20 10:00:00', '2026-08-20 10:00:00')"
        )
        sid = cur.lastrowid
        conn.executemany(
            "INSERT INTO training_split_items (split_id, dia, orden, item_type,"
            " ejercicio, grupo_muscular) VALUES (?, ?, ?, 'ejercicio', ?, ?)",
            [(sid, "LUNES", i + 1, "Press", "Pectoral") for i in range(5)]
            + [(sid, "MARTES", i + 1, "Curl", "Biceps") for i in range(5)],
        )
        conn.commit()
    finally:
        conn.close()


def _encaje(page, url, w, h, minima_altura):
    page.set_viewport_size({"width": w, "height": h})
    page.goto(url)
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_timeout(600)
    m = page.evaluate(
        "() => ({sh: document.scrollingElement.scrollHeight, ih: window.innerHeight})"
    )
    assert m["sh"] <= m["ih"] + 2, (url, w, h, m)
    assert m["sh"] >= m["ih"] - minima_altura, (url, w, h, m)


def test_encaje_exacto_1440x900(page, server, server_db_path):
    _seed(server_db_path)
    for tab in TABS:
        _encaje(page, server + tab, 1440, 900, 60)


def test_encaje_exacto_1280x1024(page, server, server_db_path):
    _seed(server_db_path)
    for tab in TABS:
        _encaje(page, server + tab, 1280, 1024, 60)


def test_fallback_1280x800_sin_scroll_global(page, server, server_db_path):
    _seed(server_db_path)
    for tab in TABS:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(server + tab)
        page.wait_for_function("document.body.dataset.appReady === '1'")
        page.wait_for_timeout(600)
        m = page.evaluate(
            "() => ({sh: document.scrollingElement.scrollHeight, ih: window.innerHeight})"
        )
        assert m["sh"] <= m["ih"] + 2, (tab, m)
