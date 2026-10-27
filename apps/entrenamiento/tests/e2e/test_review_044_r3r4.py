"""Revisión independiente: borradores posteriores y errores de dominio."""

import sqlite3

from playwright.sync_api import expect


def _open(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady==='1'")


def _question(page):
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]")
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")


def test_review_success_keeps_later_names_edit(page, server, server_db_path):
    _open(page, server)
    page.locator("#rumbo-t1-nombre").fill("VERSION ENVIADA")
    page.locator("#rumbo-t1").fill("8")
    held = {}
    page.route("**/rumbo/yo", lambda r: held.setdefault("names", r))
    page.route("**/rumbo/dia", lambda r: held.setdefault("day", r))
    page.locator('.workspace-nav a[href="/"]').click()
    page.locator("#confirm-save").click()
    for _ in range(100):
        if len(held) == 2:
            break
        page.wait_for_timeout(20)
    assert len(held) == 2
    page.locator("#rumbo-t1-nombre").fill("VERSION POSTERIOR SIN GUARDAR")
    with page.expect_response(lambda r: r.url.endswith("/rumbo/yo")):
        held["names"].continue_()
    page.wait_for_timeout(200)
    with page.expect_response(lambda r: r.url.endswith("/rumbo/dia")):
        held["day"].continue_()
    page.wait_for_timeout(400)
    with sqlite3.connect(str(server_db_path)) as conn:
        assert conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()[0] == "VERSION ENVIADA"
    assert page.url.endswith("/rumbo"), "Se navegó aunque había una edición posterior sin guardar"
    expect(page.locator("#rumbo-t1-nombre")).to_have_value("VERSION POSTERIOR SIN GUARDAR")


def test_review_domain_error_inside_modal(page, server):
    _open(page, server)
    _question(page)
    page.locator("#rumbo-respuesta-texto").fill("   ")
    with page.expect_response(lambda r: r.url.endswith("/rumbo/respuesta")) as result:
        page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    assert result.value.status == 400
    expect(page.locator("#rumbo-pregunta-dialog")).to_be_visible()
    page.screenshot(path=".tmp/review/r4-domain-error.png")
    expect(page.locator("#rumbo-respuesta-notice .notice-error")).to_be_visible(timeout=1500)


def test_review_response_success_keeps_later_edit(page, server):
    _open(page, server)
    _question(page)
    page.locator("#rumbo-respuesta-texto").fill("RESPUESTA ENVIADA")
    held = {}
    page.route("**/rumbo/respuesta", lambda r: held.setdefault("response", r))
    page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(20)
    assert held
    page.locator("#rumbo-respuesta-texto").fill("RESPUESTA POSTERIOR SIN GUARDAR")
    with page.expect_response(lambda r: r.url.endswith("/rumbo/respuesta")):
        held["response"].continue_()
    page.wait_for_timeout(300)
    expect(page.locator("#rumbo-pregunta-dialog")).to_be_visible(timeout=1500)
    expect(page.locator("#rumbo-respuesta-texto")).to_have_value("RESPUESTA POSTERIOR SIN GUARDAR")
