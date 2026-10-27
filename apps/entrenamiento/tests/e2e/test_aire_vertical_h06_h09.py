"""H06+H09 (spec 046): alturas por estado y vacío anual explícito."""

from playwright.sync_api import expect


def _open_diario(page, server):
    page.goto(server + "/diario")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#session-form", timeout=5000)


def _altura_tabla(page, panel):
    return page.evaluate(
        """(sel) => document.querySelector(sel).getBoundingClientRect().height""",
        f"#{panel} .table-scroll",
    )


def test_h06_sesion_compacta_con_una_fila_movil(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    assert page.locator("#set-rows .set-row").count() >= 1
    h = _altura_tabla(page, "session-editor")
    assert h < 452, f"tabla sesión sigue fija en 452px con 1 fila: {h}"
    y = page.locator("#edit-actions").evaluate("el => el.getBoundingClientRect().y")
    assert y < 800, f"Guardar fuera del primer viewport: y={y}"


def test_h06_sesion_muchas_filas_conserva_cota(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    if page.locator("#session-editor").get_attribute("data-editmode") != "1":
        page.locator("#session-editor .pencil-btn").click()
    for _ in range(25):
        page.locator("#set-rows [data-action='row-add']").first.click()
    h = _altura_tabla(page, "session-editor")
    assert h == 452, f"la cota máxima debe conservarse con muchas filas: {h}"
    desborda = page.evaluate(
        "() => { const sc = document.querySelector('#session-editor .table-scroll');"
        " return sc.scrollHeight > sc.clientHeight + 1; }"
    )
    assert desborda, "con muchas filas debe haber scroll interno"


def test_h06_nutricion_compacta_con_pocas_filas(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    page.locator('[data-action="daily-mode"][data-vista="alimentacion"]').click()
    h = _altura_tabla(page, "nutrition-panel")
    assert h < 516, f"tabla nutrición sigue fija en 516px: {h}"


def _open_rumbo(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-anual", timeout=5000)


def test_h09_anual_vacio_explicito_compacto(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    _open_rumbo(page, server)
    expect(page.locator("#rumbo-anual svg.rumbo-trend")).to_have_count(0)
    expect(page.locator("#rumbo-anual")).to_contain_text(
        "Todavía no hay puntuaciones guardadas este año"
    )
    expect(page.locator("#rumbo-anual")).not_to_contain_text("pico 0/210")
    h = page.locator("#rumbo-anual").evaluate("el => el.getBoundingClientRect().height")
    assert h < 200, f"tarjeta vacía demasiado alta: {h}px"


def test_h09_anual_con_datos_identico(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t2").fill("7")
    page.locator("#rumbo-t3").fill("9")
    page.locator('#rumbo-hoy button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-anual svg.rumbo-trend")).to_be_visible()
    expect(page.locator("#rumbo-anual")).to_contain_text("24/210")
    con_barras = page.evaluate(
        "() => [...document.querySelectorAll('.rumbo-trend rect')]"
        ".some((r) => Number(r.getAttribute('height')) > 0)"
    )
    assert con_barras, "el gráfico con datos debe mostrar barras"


def test_h06_altura_ajusta_añadir_quitar_sin_saltos(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario(page, server)
    if page.locator("#session-editor").get_attribute("data-editmode") != "1":
        page.locator("#session-editor .pencil-btn").click()
    h1 = _altura_tabla(page, "session-editor")
    page.locator("#set-rows [data-action='row-add']").first.click()
    page.locator("#set-rows [data-action='row-add']").first.click()
    h2 = _altura_tabla(page, "session-editor")
    assert h2 > h1, f"añadir filas no agranda la tabla: {h1} → {h2}"
    assert h2 - h1 == 48, f"crecimiento inesperado (2 filas × 24px): {h1} → {h2}"
    page.locator("#set-rows .set-row").nth(2).locator('[data-action="row-remove"]').click()
    page.locator("#set-rows .set-row").nth(1).locator('[data-action="row-remove"]').click()
    h3 = _altura_tabla(page, "session-editor")
    assert h3 == h1, f"quitar filas no devuelve la altura exacta: {h1} → {h2} → {h3}"
    expect(page.locator("#edit-actions button[type='submit']")).to_be_visible()
