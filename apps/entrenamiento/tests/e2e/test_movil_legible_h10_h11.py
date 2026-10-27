"""H10+H11 (spec 047): contraste y táctil en móvil."""

import pytest
from playwright.sync_api import expect


def _open_rumbo(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)


def _contraste_ayuda(page):
    return page.evaluate(
        """() => {
            const el = document.querySelector('#rumbo-anual .rumbo-hint');
            const cs = getComputedStyle(el);
            const lum = (c) => {
                const m = c.match(/[\\d.]+/g).map(Number).slice(0, 3).map((v) => {
                    v /= 255;
                    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2];
            };
            const fondo = cs.backgroundColor === 'rgba(0, 0, 0, 0)' ? 'rgb(23,23,23)' : cs.backgroundColor;
            const L1 = Math.max(lum(cs.color), lum(fondo));
            const L2 = Math.min(lum(cs.color), lum(fondo));
            return {color: cs.color, ratio: (L1 + 0.05) / (L2 + 0.05)};
        }"""
    )


def test_h10_ayuda_anual_contraste_aa(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t2").fill("7")
    page.locator("#rumbo-t3").fill("9")
    page.locator('#rumbo-hoy button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    med = _contraste_ayuda(page)
    assert med["ratio"] >= 4.5, f"contraste insuficiente: {med}"


def _open_diario_editable(page, server):
    page.goto(server + "/diario")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#session-form", timeout=5000)
    if page.locator("#session-editor").get_attribute("data-editmode") != "1":
        page.locator("#session-editor .pencil-btn").click()


def _quien_recibe(page, x, y):
    return page.evaluate(
        """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            if (!el) return null;
            const btn = el.closest ? el.closest('[data-action]') : null;
            return {
                accion: btn ? btn.dataset.action : null,
                delta: btn ? btn.dataset.delta || null : null,
                tag: el.tagName,
                name: el.getAttribute && el.getAttribute('name'),
            };
        }""",
        [x, y],
    )


def _caja(page, selector):
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            el.scrollIntoView({block: 'nearest', inline: 'center'});
            const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height};
        }""",
        selector,
    )


def test_h11_sin_hover_acciones_visibles(browser, server):
    ctx = browser.new_context(
        viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True
    )
    page = ctx.new_page()
    try:
        _open_diario_editable(page, server)
        expect(page.locator("#set-rows .set-row .row-actions").first).to_have_css(
            "opacity", "1", timeout=3000
        )
        # Nutrición comparte el patrón: visible sin hover en edición.
        page.locator('[data-action="daily-mode"][data-vista="alimentacion"]').click()
        if page.locator("#nutrition-panel").get_attribute("data-editmode") != "1":
            page.locator('[data-action="nutrition-toggle-edit"]').click()
        expect(page.locator("#nutrition-rows .nutrition-row .row-actions").first).to_have_css(
            "opacity", "1", timeout=3000
        )
    finally:
        ctx.close()


@pytest.mark.parametrize("ancho", [320, 390, 1280])
def test_h11_areas_efectivas_y_solapes(page, server, ancho):
    page.set_viewport_size({"width": ancho, "height": 800})
    _open_diario_editable(page, server)
    lapiz = _caja(page, "#session-editor .pencil-btn")
    assert lapiz["w"] >= 24 and lapiz["h"] >= 24, f"lápiz menor de 24px: {lapiz}"
    # La píldora +/−: el centro y el borde del área expandida (24px)
    # resuelven al propio botón; el punto medio entre dos filas no activa
    # un control ajeno.
    pill = _caja(page, "#set-rows .set-row .row-btn")
    cx, cy = pill["x"] + pill["w"] / 2, pill["y"] + pill["h"] / 2
    assert _quien_recibe(page, cx, cy)["accion"] in ("row-add", "row-remove")
    borde = _quien_recibe(page, cx - 10, cy)
    assert borde["accion"] in ("row-add", "row-remove"), f"expansor no cubre: {borde}"
    # RIR en la píldora: cajas 24×24, deltas exactos y paso funcional ±0,1.
    # Medición atómica por botón (desplazar, medir y pulsar sin reordenar).
    for delta in ("0.1", "-0.1"):
        hit = page.evaluate(
            """(d) => {
                const b = document.querySelector(`#set-rows .row-actions [data-delta="${d}"]`);
                b.scrollIntoView({block: 'nearest', inline: 'center'});
                const r = b.getBoundingClientRect();
                if (r.width < 24 || r.height < 24) return 'caja:' + r.width + 'x' + r.height;
                const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                const t = el && el.closest ? el.closest('[data-action]') : null;
                return t ? t.dataset.delta : null;
            }""",
            delta,
        )
        assert hit == delta, f"botón RIR {delta} no mide/resuelve 24px: {hit}"
    antes = page.locator('#set-rows input[name="rir"]').first.input_value()
    page.locator("#set-rows .set-row").first.hover()
    page.locator('#set-rows .row-actions [data-delta="0.1"]').first.click()
    expect(page.locator('#set-rows input[name="rir"]').first).not_to_have_value(antes)
    # Punto medio entre dos píldoras vecinas: resuelve a una acción de fila,
    # nunca a un control ajeno (sin superposición efectiva). Todo atómico.
    page.locator("#set-rows .set-row").first.locator('[data-action="row-add"]').click()
    medio = page.evaluate(
        """() => {
            document.querySelector('#set-rows .set-row:nth-child(1) .row-btn')
                .scrollIntoView({block: 'nearest', inline: 'center'});
            const r1 = document.querySelector('#set-rows .set-row:nth-child(1) .row-btn').getBoundingClientRect();
            const r2 = document.querySelector('#set-rows .set-row:nth-child(2) .row-btn').getBoundingClientRect();
            const el = document.elementFromPoint(r1.x, (r1.y + r2.y) / 2);
            const btn = el && el.closest ? el.closest('[data-action]') : null;
            return btn ? btn.dataset.action : null;
        }"""
    )
    assert medio in ("row-add", "row-remove"), f"solape ambiguo: {medio}"


@pytest.mark.parametrize("ancho", [320, 390, 1280])
def test_h11_rir_objetivos_reales_24px(page, server, ancho):
    """R2: los botones RIR de la píldora miden 24×24 efectivos (sin expansor)."""
    page.set_viewport_size({"width": ancho, "height": 800})
    _open_diario_editable(page, server)
    geo = page.evaluate(
        """() => ['0.1', '-0.1'].map((d) => {
            const el = document.querySelector(`#set-rows .row-actions [data-delta="${d}"]`);
            el.scrollIntoView({block: 'nearest', inline: 'center'});
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el, '::before');
            const num = (v) => parseFloat(v) || 0;
            const left = Math.min(r.left, r.left + num(s.left));
            const right = Math.max(r.right, r.right - num(s.right));
            const top = Math.min(r.top, r.top + num(s.top));
            const bottom = Math.max(r.bottom, r.bottom - num(s.bottom));
            return {w: right - left, h: bottom - top};
        })"""
    )
    for i, g in enumerate(geo):
        assert g["w"] >= 24 and g["h"] >= 24, f"mitad {i} menor de 24px: {g}"


def test_h11_pildora_boton_exacto_en_expansor(browser, server):
    """R2: un punto en el expansor declarado resuelve a SU botón, no al vecino."""
    ctx = browser.new_context(
        viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True
    )
    page = ctx.new_page()
    try:
        _open_diario_editable(page, server)
        quien = page.evaluate(
            """() => {
                const quitar = document.querySelector('#set-rows .set-row [data-action="row-remove"]');
                quitar.scrollIntoView({block: 'nearest', inline: 'center'});
                const r = quitar.getBoundingClientRect();
                const el = document.elementFromPoint(r.left + r.width / 2 + 10, r.top + r.height / 2);
                const btn = el && el.closest ? el.closest('[data-action]') : null;
                return btn ? btn.dataset.action : null;
            }"""
        )
        assert quien == "row-remove", f"el expansor de eliminar activa {quien}"
    finally:
        ctx.close()


def test_h11_inputs_vecinos_horizontales_resuelven_campo(page, server):
    """Los fallos laterales entre inputs no activan acciones (campo o hueco inerte)."""
    page.set_viewport_size({"width": 390, "height": 800})
    _open_diario_editable(page, server)
    res = page.evaluate(
        """() => {
            const kg = document.querySelector('#set-rows input[name="kg"]');
            kg.scrollIntoView({block: 'nearest', inline: 'center'});
            const a = kg.getBoundingClientRect();
            const reps = document.querySelector('#set-rows input[name="reps"]');
            const b = reps.getBoundingClientRect();
            const el = document.elementFromPoint((a.right + b.left) / 2, (a.top + a.bottom) / 2);
            const btn = el && el.closest ? el.closest('[data-action]') : null;
            return {
                accion: btn ? btn.dataset.action : null,
                nombre: el && el.getAttribute ? el.getAttribute('name') : null,
                tag: el ? el.tagName : null,
            };
        }"""
    )
    assert res["accion"] is None, f"un fallo lateral activa una acción: {res}"


def test_h11_pildora_ampliada_no_tapa_valores(browser, server):
    """La píldora con 4 botones no oculta los valores de la fila en táctil."""
    ctx = browser.new_context(
        viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True
    )
    page = ctx.new_page()
    try:
        _open_diario_editable(page, server)
        page.locator("#set-rows .set-row").first.locator("select[name='ejercicio']").select_option(
            "Press"
        )
        page.locator('#set-rows input[name="kg"]').first.fill("80")
        res = page.evaluate(
            """() => {
                const out = {};
                for (const name of ["kg", "descanso"]) {
                    const inp = document.querySelector(`#set-rows input[name="${name}"]`);
                    inp.scrollIntoView({block: 'nearest', inline: 'center'});
                    const r = inp.getBoundingClientRect();
                    const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                    const btn = el && el.closest ? el.closest('[data-action]') : null;
                    out[name] = {centro: el === inp, accion: btn ? btn.dataset.action : null};
                }
                const pill = document.querySelector('#set-rows .set-row .row-actions');
                const pr = pill.getBoundingClientRect();
                const td = pill.closest('td').getBoundingClientRect();
                out.contenida = pr.left >= td.left - 1 && pr.right <= td.right + 1;
                out.pildora = {w: Math.round(pr.width), h: Math.round(pr.height)};
                return out;
            }"""
        )
        assert res["contenida"], f"la píldora desborda su cuneta: {res}"
        assert res["kg"]["centro"], f"valor de Peso tapado por la píldora: {res}"
        assert res["descanso"]["centro"], f"valor de Descanso tapado: {res}"
        assert res["kg"]["accion"] is None and res["descanso"]["accion"] is None, res
    finally:
        ctx.close()


def test_h11_escritorio_hover_boton_exacto_sin_vecino(page, server):
    """R2d: con hover activo, los puntos declarados de cada botón resuelven a él."""
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_diario_editable(page, server)
    page.locator("#set-rows .set-row").first.hover()
    for accion, deltas in (("row-remove", [-8, 0, 6]), ("row-add", [-6, 0, 6])):
        for dx in deltas:
            quien = page.evaluate(
                """([accion, dx]) => {
                    const btns = [...document.querySelectorAll(
                        '#set-rows .set-row:first-child .row-actions [data-action="' + accion + '"]')];
                    const b = btns[0];
                    b.scrollIntoView({block: 'nearest', inline: 'center'});
                    const r = b.getBoundingClientRect();
                    const el = document.elementFromPoint(r.left + r.width / 2 + dx, r.top + r.height / 2);
                    const t = el && el.closest ? el.closest('[data-action]') : null;
                    return t ? t.dataset.action : null;
                }""",
                [accion, dx],
            )
            assert quien == accion, f"escritorio: {dx:+d}px en {accion} activa {quien}"


@pytest.mark.parametrize("ancho,tactil", [(1280, False), (390, True)])
def test_h11_nutricion_boton_exacto(browser, server, ancho, tactil):
    """R2d2: en nutrición cada punto declarado resuelve a su propio botón."""
    kw = {"viewport": {"width": ancho, "height": 800}}
    if tactil:
        kw.update(has_touch=True, is_mobile=True)
    ctx = browser.new_context(**kw)
    page = ctx.new_page()
    try:
        _open_diario_editable(page, server)
        page.locator('[data-action="daily-mode"][data-vista="alimentacion"]').click()
        if page.locator("#nutrition-panel").get_attribute("data-editmode") != "1":
            page.locator('[data-action="nutrition-toggle-edit"]').click()
        page.locator("#nutrition-rows .nutrition-row").first.hover()
        for accion, deltas in (
            # Lados enfrentados entre botones (el +8 de `add` caería fuera
            # del scrollport en el límite de la tabla: zona muerta inerte,
            # no verificable ni activable).
            ("nutrition-row-remove", [-8, 0, 8]),
            ("nutrition-row-add", [-8, 0]),
        ):
            for dx in deltas:
                quien = page.evaluate(
                    """([accion, dx]) => {
                        const b = document.querySelector(
                            '#nutrition-rows .nutrition-row:first-child .row-actions [data-action="' +
                                accion +
                                '"]'
                        );
                        b.scrollIntoView({block: 'nearest', inline: 'center'});
                        const r = b.getBoundingClientRect();
                        const el = document.elementFromPoint(r.left + r.width / 2 + dx, r.top + r.height / 2);
                        const t = el && el.closest ? el.closest('[data-action]') : null;
                        return t ? t.dataset.action : null;
                    }""",
                    [accion, dx],
                )
                assert quien == accion, f"nutrición {ancho}px: {dx:+d}px en {accion} activa {quien}"
    finally:
        ctx.close()
