"""Browser test de Rumbo simple: sliders → guardar → score, semana y año (spec 019)."""

from playwright.sync_api import expect


def test_rumbo_sliders_actualizan_todo(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)

    # Cabecera, tendencia, semana y hoy visibles.
    expect(page.locator("#rumbo-yo")).to_be_visible()
    expect(page.locator("#rumbo-anual")).to_be_visible()
    expect(page.locator("#rumbo-semana")).to_be_visible()

    # Jerarquía original: títulos borgoña a 12px (revertido a canónico).
    expect(page.locator("#rumbo-hoy .panel-title").first).to_have_css("color", "rgb(229, 109, 136)")
    expect(page.locator("#rumbo-hoy .panel-title").first).to_have_css("font-size", "12px")
    # Mueve sliders a 8/7/9 y guarda: score 24/30 en hoy, semana y año.
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t2").fill("7")
    page.locator("#rumbo-t3").fill("9")
    page.click('#rumbo-hoy button[type="submit"]')
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-hoy")).to_contain_text("24/30")
    expect(page.locator("#rumbo-semana")).to_contain_text("24/210")


def test_rumbo_pregunta_actualizar_apila(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-preguntas", timeout=5000)

    # Sidebar índice: filas sin bordes, alto completo.
    expect(page.locator("#rumbo-preguntas .rumbo-indice-fila").first).to_be_visible()
    expect(page.locator("#rumbo-preguntas .rumbo-indice-titulo").first).to_have_css(
        "color", "rgb(255, 255, 255)"
    )
    expect(page.locator("#rumbo-preguntas .rumbo-indice-titulo").first).to_have_css(
        "font-size", "13px"
    )
    expect(page.locator("#rumbo-preguntas .rumbo-indice-fila").first).to_have_css(
        "border-top-width", "0px"
    )
    # Spec 035/040: aside sin barra visible pero con scroll (desktop ≥1024px).
    # La regla vive en el vocabulario canónico (components.css), no en rumbo.css.
    css = page.request.get(f"{server}/static/css/components.css").text()
    assert "scrollbar-width: none" in css
    assert ".splits-catalog-col::-webkit-scrollbar" in css
    aside = page.locator(".rumbo-page .splits-catalog-col")
    assert aside.evaluate("el => getComputedStyle(el).scrollbarWidth") == "none"
    assert aside.evaluate("el => getComputedStyle(el).overflowY") == "auto"
    assert aside.evaluate("el => el.scrollHeight > el.clientHeight")
    expect(page.locator("#rumbo-preguntas .rumbo-indice-fila").first).to_have_css(
        "padding-left", "12px"
    )
    alto_aside = page.locator("#rumbo-preguntas").evaluate(
        "el => el.getBoundingClientRect().height"
    )
    assert alto_aside > 700
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    alto_1 = page.locator("#rumbo-pregunta-dialog").evaluate(
        "el => el.getBoundingClientRect().height"
    )
    expect(page.locator("#rumbo-pregunta-title")).to_contain_text("insatisfacción")
    expect(page.locator(".rumbo-respuesta-grande")).to_contain_text("tolerar")
    expect(page.locator('#rumbo-pregunta-dialog button[type="submit"]')).not_to_be_visible()
    # Nav sin borde ni fondo.
    expect(page.locator(".rumbo-pregunta-nav .btn").first).to_have_css(
        "border-top-color", "rgba(0, 0, 0, 0)"
    )
    # Con una sola respuesta no hay historial visible.
    expect(page.locator("#rumbo-pregunta-dialog .rumbo-historial")).to_have_count(0)
    # Nav clavada abajo aunque el contenido sea corto.
    pos = page.locator("#rumbo-pregunta-dialog").evaluate(
        """el => {
            const nav = el.querySelector('.rumbo-pregunta-nav').getBoundingClientRect();
            const box = el.getBoundingClientRect();
            return {navBottom: nav.bottom, boxBottom: box.bottom};
        }"""
    )
    assert abs(pos["boxBottom"] - pos["navBottom"]) < 64

    # Anterior/siguiente navega sin cerrar; Agregar despliega y guardar apila.
    page.click('#rumbo-pregunta-dialog nav button:has-text("Quejas repetidas")')
    expect(page.locator("#rumbo-pregunta-title")).to_contain_text("quejas")
    alto_2 = page.locator("#rumbo-pregunta-dialog").evaluate(
        "el => el.getBoundingClientRect().height"
    )
    assert alto_1 == alto_2
    page.click('#rumbo-pregunta-dialog nav button:has-text("Insatisfacción")')
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("Mi respuesta nueva e2e")
    page.click('#rumbo-pregunta-dialog button[type="submit"]')
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()


def test_rumbo_shell_estandar_en_desktop(page, server):
    """Spec 040: Rumbo usa el shell estándar (sticky + scroll por columna, sin
    100vh fijo): el aside es sticky con scroll interno invisible y la página
    puede desplazar en vertical como Splits/Diario; sin overflow horizontal."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-preguntas", timeout=5000)
    aside = page.locator(".rumbo-page .splits-catalog-col")
    assert aside.evaluate("el => getComputedStyle(el).position") == "sticky"
    assert aside.evaluate("el => getComputedStyle(el).overflowY") == "auto"
    assert aside.evaluate("el => getComputedStyle(el).scrollbarWidth") == "none"
    assert aside.evaluate("el => el.scrollHeight > el.clientHeight")
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )
    assert (
        page.evaluate("getComputedStyle(document.querySelector('.rumbo-page')).overflow")
        == "visible"
    )


def test_rumbo_header_identico_al_resto(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-preguntas", timeout=5000)
    expect(page.locator(".rumbo-page .splits-page-header h1")).to_have_text("Senda")
    expect(page.locator(".rumbo-page")).to_have_css("padding-top", "24px")


def test_rumbo_fondo_con_aire_en_desktop(page, server):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-yo", timeout=5000)
    pos = page.locator(".rumbo-page .splits-editor-col").evaluate(
        """el => {
            el.scrollTop = el.scrollHeight;
            const btns = [...el.querySelectorAll('button[type="submit"]')];
            const last = btns[btns.length - 1];
            const cb = el.getBoundingClientRect();
            const lb = last.getBoundingClientRect();
            return {gap: cb.bottom - lb.bottom, txt: last.textContent.trim()};
        }"""
    )
    assert pos["txt"] == "Guardar nombres"
    assert pos["gap"] >= 16


def test_rumbo_con_scroll_de_pagina_en_movil(page, server):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)
    con_scroll = page.evaluate("document.scrollingElement.scrollHeight > window.innerHeight + 1")
    assert con_scroll
