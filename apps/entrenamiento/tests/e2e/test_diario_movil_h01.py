"""H01: columna Ejercicio legible en móvil (spec 044 T2, prueba que falla)."""

from playwright.sync_api import expect


def _open_diario(page, server):
    page.goto(server + "/diario")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#session-form", timeout=5000)


def _medir_ejercicio(page):
    return page.evaluate(
        """() => {
            const sel = document.querySelector('#set-rows .set-row select[name="ejercicio"]');
            const td = sel ? sel.closest('td') : null;
            const table = document.querySelector('#session-editor .table-scroll table');
            const sc = document.querySelector('#session-editor .table-scroll');
            const sr = sel ? sel.getBoundingClientRect() : null;
            const tr = td ? td.getBoundingClientRect() : null;
            return {
                selW: sr ? sr.width : 0,
                selH: sr ? sr.height : 0,
                tdW: tr ? tr.width : 0,
                tableScroll: table ? table.scrollWidth : 0,
                tableClient: table ? table.clientWidth : 0,
                scrollClient: sc ? sc.clientWidth : 0,
                docOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
                overflowX: sc ? getComputedStyle(sc).overflowX : '',
            };
        }"""
    )


def _asegurar_editable(page):
    if page.locator("#session-editor").get_attribute("data-editmode") != "1":
        page.locator("#session-editor .pencil-btn").click()


def _caso(viewport, modo):
    return f"{viewport}px/{modo}"


def test_h01_ejercicio_legible_390_fuerza(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    _asegurar_editable(page)
    m = _medir_ejercicio(page)
    assert m["selW"] >= 120, f"selector colapsado a 390 fuerza: {m}"
    assert m["tdW"] >= 120, f"celda colapsada a 390 fuerza: {m}"
    assert not m["docOverflow"], f"desbordamiento global: {m}"
    assert m["overflowX"] in ("auto", "scroll"), m


def test_h01_ejercicio_legible_320_fuerza(page, server):
    page.set_viewport_size({"width": 320, "height": 800})
    _open_diario(page, server)
    _asegurar_editable(page)
    m = _medir_ejercicio(page)
    assert m["selW"] >= 100, f"selector colapsado a 320 fuerza: {m}"
    assert m["tdW"] >= 100, f"celda colapsada a 320 fuerza: {m}"
    assert not m["docOverflow"], f"desbordamiento global: {m}"


def test_h01_ejercicio_legible_390_hiit(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    _asegurar_editable(page)
    page.locator("#set-rows .set-row").first.locator("select[name='ejercicio']").select_option(
        "HIIT"
    )
    page.wait_for_timeout(300)
    m = _medir_ejercicio(page)
    assert m["selW"] >= 120, f"selector colapsado a 390 HIIT: {m}"
    assert m["tdW"] >= 120, f"celda colapsada a 390 HIIT: {m}"
    assert not m["docOverflow"], f"desbordamiento global: {m}"


def test_h01_ejercicio_nombre_largo_390(page, server, server_db_path):
    import sqlite3

    largo = "Press de banca con barra olímpica larga"
    conn = sqlite3.connect(str(server_db_path))
    try:
        conn.execute(
            "INSERT INTO ejercicios (ejercicio, grupo_muscular, categoria) VALUES (?, ?, ?)",
            (largo, "Pectoral", "EMPUJE"),
        )
        conn.commit()
    finally:
        conn.close()
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    _asegurar_editable(page)
    page.locator("#set-rows .set-row").first.locator("select[name='ejercicio']").select_option(
        largo
    )
    page.wait_for_timeout(300)
    m = _medir_ejercicio(page)
    assert m["selW"] >= 120, f"selector colapsado con nombre largo: {m}"
    assert m["tdW"] >= 120, f"celda colapsada con nombre largo: {m}"
    assert not m["docOverflow"], f"desbordamiento global: {m}"
    # El selector sigue siendo operable con el nombre largo.
    expect(
        page.locator("#set-rows .set-row").first.locator("select[name='ejercicio']")
    ).to_have_value(largo)
