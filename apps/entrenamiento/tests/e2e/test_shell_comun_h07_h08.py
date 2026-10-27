"""H07+H08 (spec 048): anchos y cabecera comunes."""


def _col(page):
    return page.evaluate(
        """() => {
            const c = document.querySelector('.splits-editor-col');
            const r = c.getBoundingClientRect();
            return {x: Math.round(r.x), w: Math.round(r.width)};
        }"""
    )


def test_h07_ancho_editor_diario_como_splits_rumbo(page, server):
    page.set_viewport_size({"width": 1440, "height": 900})
    anchos = {}
    for path in ("/diario", "/splits", "/rumbo"):
        page.goto(server + path)
        page.wait_for_function("document.body.dataset.appReady === '1'")
        anchos[path] = _col(page)
    assert anchos["/diario"] == anchos["/splits"] == anchos["/rumbo"], anchos


def _cabecera(page):
    return page.evaluate(
        """() => {
            const nav = document.querySelector('.workspace-nav').getBoundingClientRect();
            const head = document.querySelector('.splits-page-header').getBoundingClientRect();
            return {navX: Math.round(nav.x), headH: Math.round(head.height)};
        }"""
    )


def test_h08_cabecera_estable_y_toolbar(page, server):
    page.set_viewport_size({"width": 1440, "height": 900})
    medidas = {}
    for path in ("/diario", "/splits", "/rumbo"):
        page.goto(server + path)
        page.wait_for_function("document.body.dataset.appReady === '1'")
        medidas[path] = _cabecera(page)
    xs = sorted(m["navX"] for m in medidas.values())
    assert xs[-1] - xs[0] <= 1, f"navegación desplazada según pestaña: {medidas}"
    alturas = {m["headH"] for m in medidas.values()}
    assert len(alturas) == 1, f"cabeceras de distinta altura: {medidas}"
    # «Nuevo split» vive en la cabecera del aside (no en la fila de la marca).
    page.goto(server + "/splits")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    boton = page.locator("aside.splits-catalog-col .splits-aside-actions button")
    assert boton.is_visible()
    assert page.locator(".splits-page-header button").count() == 0


def test_h08_cabecera_movil_sin_desplazamientos(page, server):
    page.set_viewport_size({"width": 390, "height": 800})
    medidas = {}
    for path in ("/diario", "/splits", "/rumbo"):
        page.goto(server + path)
        page.wait_for_function("document.body.dataset.appReady === '1'")
        medidas[path] = _cabecera(page)
    xs = sorted(m["navX"] for m in medidas.values())
    assert xs[-1] - xs[0] <= 1, f"navegación desplazada en móvil: {medidas}"
    desborda = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")
    assert not desborda, "desbordamiento horizontal en móvil"
