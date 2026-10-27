"""Spec 039 T4: recarga con selección servida hace cero /grafica (RF-1)."""

from playwright.sync_api import expect


def test_recarga_con_seleccion_cero_grafica(page, server, server_db_path):
    import sqlite3

    conn = sqlite3.connect(str(server_db_path))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios (grupo_muscular, ejercicio) "
            "VALUES ('Pectoral', 'Press')"
        )
        conn.execute(
            "INSERT INTO training_sets (semana, dia, fecha, set_orden, ejercicio, "
            "reps, kg, rir) VALUES (10, 'LUNES', '2026-08-18', 1, 'Press', 8, 100, 2)"
        )
        conn.commit()
    finally:
        conn.close()
    reqs: list[str] = []
    page.on("request", lambda r: reqs.append(r.url) if "/grafica" in r.url else None)
    page.goto(f"{server}/?musculos=Pectoral")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_timeout(1500)
    pressed = page.locator('#dashboard-catalog [data-foco="Pectoral"][aria-pressed="true"]')
    expect(pressed).to_be_visible()
    reqs.clear()
    page.reload()
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_timeout(2000)
    assert reqs == [], reqs
    expect(
        page.locator('#dashboard-catalog [data-foco="Pectoral"][aria-pressed="true"]')
    ).to_be_visible()


def _sembrar_pectoral(server_db_path):
    import sqlite3

    conn = sqlite3.connect(str(server_db_path))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios (grupo_muscular, ejercicio) "
            "VALUES ('Pectoral', 'Press')"
        )
        conn.execute(
            "INSERT INTO training_sets (semana, dia, fecha, set_orden, ejercicio, "
            "reps, kg, rir) VALUES (10, 'LUNES', '2026-08-18', 1, 'Press', 8, 100, 2)"
        )
        conn.commit()
    finally:
        conn.close()


def test_rects_estables_tras_asentado(page, server, server_db_path):
    """Spec 039 RF-2: las columnas no cambian de dimensiones entre el primer
    pintado y el asentado (sin deltas por medición JS)."""
    _sembrar_pectoral(server_db_path)
    page.goto(f"{server}/?musculos=Pectoral")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    sels = [
        ".dashboard-catalog-col",
        ".dashboard-summary-col",
        "#period-summary-wrap",
        "#unified-chart-container",
    ]
    primero = page.evaluate(
        "(sels) => sels.map((s) => { const r = document.querySelector(s).getBoundingClientRect();"
        " return [r.height, r.y]; })",
        sels,
    )
    page.wait_for_timeout(2000)
    despues = page.evaluate(
        "(sels) => sels.map((s) => { const r = document.querySelector(s).getBoundingClientRect();"
        " return [r.height, r.y]; })",
        sels,
    )
    for sel, antes, ahora in zip(sels, primero, despues):
        assert abs(antes[0] - ahora[0]) < 1, (sel, antes, ahora)
        assert abs(antes[1] - ahora[1]) < 1, (sel, antes, ahora)
