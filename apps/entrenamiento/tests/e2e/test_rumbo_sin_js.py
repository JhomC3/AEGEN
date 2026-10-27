"""H04 (spec 045): Rumbo sin JavaScript declara el requisito con honestidad.

Con JS desactivado: aviso honesto visible, botones de envío ocultos (ningún
control ofrece guardar ni provoca GET con datos) y lectura servida intacta.
"""

from urllib.parse import urlsplit

from playwright.sync_api import expect


def _open_sin_js(browser, server):
    ctx = browser.new_context(java_script_enabled=False)
    page = ctx.new_page()
    page.goto(server + "/rumbo")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)
    return ctx, page


def test_h04_sin_js_aviso_honesto_y_sin_promesa_de_guardado(browser, server):
    ctx, page = _open_sin_js(browser, server)
    try:
        # Sin JS el contenido de <noscript> se sirve y renderiza como aviso.
        html = page.content()
        assert "Rumbo necesita JavaScript para guardar" in html
        assert "guardan igual" not in html
        expect(page.locator("div.notice")).to_be_visible()
    finally:
        ctx.close()


def test_h04_sin_js_envios_ocultos_y_lectura_intacta(browser, server):
    ctx, page = _open_sin_js(browser, server)
    try:
        # Ningún control ofrece guardar.
        expect(page.locator('#rumbo-hoy button[type="submit"]')).not_to_be_visible()
        expect(page.locator('#rumbo-yo button[type="submit"]')).not_to_be_visible()
        # La lectura servida sigue disponible.
        expect(page.locator("#rumbo-hoy")).to_be_visible()
        expect(page.locator("#rumbo-semana")).to_be_visible()
        expect(page.locator("#rumbo-anual")).to_be_visible()
        expect(page.locator("#rumbo-preguntas")).to_be_visible()
    finally:
        ctx.close()


def test_h04_sin_js_enter_no_envia_por_get(browser, server):
    ctx, page = _open_sin_js(browser, server)
    enviados = []
    page.on("request", lambda r: enviados.append(r))
    try:
        page.locator("#rumbo-t1-nombre").fill("BORRADOR NO DEBE ENVIARSE")
        # Sin botón de envío operativo no hay submit implícito por Enter.
        expect(page.locator('#rumbo-hoy button[type="submit"]')).to_be_disabled()
        expect(page.locator('#rumbo-yo button[type="submit"]')).to_be_disabled()
        page.locator("#rumbo-t1-nombre").press("Enter")
        page.wait_for_timeout(400)
        mal = [
            r
            for r in enviados
            if r.method == "GET" and urlsplit(r.url).path == "/rumbo" and urlsplit(r.url).query
        ]
        assert not mal, "Enter envía los datos del formulario por GET sin JavaScript"
        assert page.url.split("?")[0].endswith("/rumbo")
    finally:
        ctx.close()
