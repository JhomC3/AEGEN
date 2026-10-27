"""H02: errores de guardado de Rumbo con feedback visible (spec 044 T4)."""

import sqlite3
import time

from playwright.sync_api import expect


def _open_rumbo(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)


def _rumbo_dia(db_path, fecha):
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT t1, t2, t3 FROM rumbo_dia WHERE fecha = ?", (fecha,)).fetchone()
    finally:
        conn.close()


def test_h02_rumbo_dia_500_avisa_y_conserva(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.route(
        "**/rumbo/dia",
        lambda route: route.fulfill(status=500, body="<html>boom</html>"),
    )
    page.locator('#rumbo-hoy button[type="submit"]').click()
    expect(page.locator("#notice-container .notice-error")).to_be_visible(timeout=5000)
    expect(page.locator("#notice-container")).to_contain_text("no se guard")
    # Valores conservados y reintento posible.
    expect(page.locator("#rumbo-t1")).to_have_value("8")
    expect(page.locator('#rumbo-hoy button[type="submit"]')).to_be_enabled()
    page.unroute("**/rumbo/dia")


def test_h02_rumbo_dia_red_avisa_y_conserva(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t2").fill("9")

    def _abort(route):
        route.abort()

    page.route("**/rumbo/dia", _abort)
    page.locator('#rumbo-hoy button[type="submit"]').click()
    expect(page.locator("#notice-container .notice-error")).to_be_visible(timeout=5000)
    expect(page.locator("#rumbo-t2")).to_have_value("9")
    expect(page.locator('#rumbo-hoy button[type="submit"]')).to_be_enabled()
    page.unroute("**/rumbo/dia")


def test_h02_rumbo_yo_500_avisa_y_reintento_persiste(page, server, server_db_path):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill(" shipped")
    page.route(
        "**/rumbo/yo",
        lambda route: route.fulfill(status=500, body="<html>boom</html>"),
    )
    page.locator('#rumbo-yo button[type="submit"]').click()
    expect(page.locator("#notice-container .notice-error")).to_be_visible(timeout=5000)
    expect(page.locator("#rumbo-t1-nombre")).to_have_value(" shipped")
    page.unroute("**/rumbo/yo")
    # Reintento tras el fallo: persiste de verdad.
    page.locator("#rumbo-t1-nombre").fill("Deep Work")
    page.locator('#rumbo-yo button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    conn = sqlite3.connect(str(server_db_path))
    try:
        row = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert row is not None and row[0] == "Deep Work", row


def test_h02_rumbo_doble_clic_una_peticion(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("7")
    posts = []
    page.on(
        "request",
        lambda r: posts.append(r.url) if r.method == "POST" and "/rumbo/dia" in r.url else None,
    )

    def _lento(route):
        time.sleep(0.6)
        route.fulfill(
            status=200,
            body='<div id="notice-container" hx-swap-oob="innerHTML">'
            '<div class="notice notice-success">Día registrado: 17/30.</div></div>',
        )

    page.route("**/rumbo/dia", _lento)
    page.evaluate(
        """() => {
            const btn = document.querySelector('#rumbo-hoy button[type="submit"]');
            btn.click();
            btn.click();
        }"""
    )
    page.wait_for_function(
        """() => {
            const b = document.querySelector('#rumbo-hoy button[type="submit"]');
            return b && b.textContent.trim().startsWith('Guardando');
        }""",
        timeout=3000,
    )
    page.wait_for_timeout(900)
    assert len(posts) == 1, f"doble clic generó {len(posts)} peticiones"
    page.unroute("**/rumbo/dia")


def test_h02_rumbo_respuesta_500_aviso_dentro_dialogo(page, server):
    from pathlib import Path

    _open_rumbo(page, server)
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("respuesta R4 que debe conservarse")
    page.route(
        "**/rumbo/respuesta",
        lambda route: route.fulfill(status=500, body="<html>boom</html>"),
    )
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    aviso = page.locator("#rumbo-pregunta-dialog .notice-error")
    expect(aviso).to_be_visible(timeout=5000)
    # El aviso está dentro del modal visible (no detrás del backdrop).
    dentro = page.evaluate(
        """() => {
            const d = document.querySelector('#rumbo-pregunta-dialog').getBoundingClientRect();
            const n = document.querySelector('#rumbo-pregunta-dialog .notice-error').getBoundingClientRect();
            return n.width > 50 && n.top >= d.top - 1 && n.bottom <= d.bottom + 1
                && n.left >= d.left - 1 && n.right <= d.right + 1;
        }"""
    )
    assert dentro, "el aviso de error no está legible dentro del diálogo"
    root = Path(__file__).resolve().parents[2]
    page.screenshot(path=str(root / ".tmp" / "evidence-lote-044" / "h02-rumbo-respuesta-error.png"))
    # La respuesta se conserva y el reintento funciona.
    expect(page.locator("#rumbo-respuesta-texto")).to_have_value(
        "respuesta R4 que debe conservarse"
    )
    page.unroute("**/rumbo/respuesta")
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()


def test_h02_rumbo_respuesta_400_aviso_dentro_dialogo(page, server):
    _open_rumbo(page, server)
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    # Solo espacios: el servidor lo recorta a vacío y responde 400.
    page.locator("#rumbo-respuesta-texto").fill("   ")
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    aviso = page.locator("#rumbo-pregunta-dialog .notice-error")
    expect(aviso).to_be_visible(timeout=5000)
    dentro = page.evaluate(
        """() => {
            const d = document.querySelector('#rumbo-pregunta-dialog').getBoundingClientRect();
            const n = document.querySelector('#rumbo-pregunta-dialog .notice-error').getBoundingClientRect();
            return n.width > 50 && n.top >= d.top - 1 && n.bottom <= d.bottom + 1
                && n.left >= d.left - 1 && n.right <= d.right + 1;
        }"""
    )
    assert dentro, "el aviso 400 no está legible dentro del diálogo"
    # El texto se conserva y el reintento con contenido válido guarda.
    expect(page.locator("#rumbo-respuesta-texto")).to_have_value("   ")
    page.locator("#rumbo-respuesta-texto").fill("respuesta válida tras 400")
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()
