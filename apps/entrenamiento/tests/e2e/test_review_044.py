"""Revisión independiente: contratos cruzados de pendientes Rumbo."""

import sqlite3

from playwright.sync_api import expect


def _open(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")


def _dirty(page):
    return page.evaluate("async()=> (await import('/static/js/rumbo.js')).rumboIsDirty()")


def test_review_save_day_keeps_unsaved_names_dirty(page, server, server_db_path):
    _open(page, server)
    page.locator("#rumbo-t1-nombre").fill("NO GUARDADO REVISIÓN")
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-hoy button[type=submit]").click()
    page.wait_for_selector("#notice-container .notice-success")
    page.wait_for_timeout(300)
    with sqlite3.connect(server_db_path) as conn:
        saved = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    print(
        {
            "names_on_screen": page.locator("#rumbo-t1-nombre").input_value(),
            "names_in_db": saved,
            "dirty": _dirty(page),
        }
    )
    assert _dirty(page), "Guardar el día eliminó la protección de nombres que siguen sin guardar"


def test_review_partial_save_failure_does_not_navigate(page, server, server_db_path):
    _open(page, server)
    page.locator("#rumbo-t1-nombre").fill("NOMBRES CON FALLO")
    page.locator("#rumbo-t1").fill("8")
    page.route("**/rumbo/yo", lambda r: r.fulfill(status=500, body="Fallo nombres"))
    page.locator('.workspace-nav a[href="/"]').click()
    page.locator("#confirm-save").click()
    page.wait_for_timeout(1800)
    with sqlite3.connect(server_db_path) as conn:
        saved = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    print({"url_after_partial_save": page.url, "names_in_db": saved})
    assert page.url.endswith("/rumbo"), "Navegó aunque falló uno de los formularios pendientes"
    expect(page.locator("#rumbo-t1-nombre")).to_have_value("NOMBRES CON FALLO")


def test_review_escape_cancels_pending_navigation(page, server):
    _open(page, server)
    page.locator("#rumbo-t1-nombre").fill("GUARDAR QUEDÁNDOME")
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#confirm-modal")).not_to_be_visible()
    page.locator("#rumbo-yo button[type=submit]").click()
    page.wait_for_timeout(1000)
    print({"url_after_escape_and_save": page.url})
    assert page.url.endswith(
        "/rumbo"
    ), "Una navegación cancelada con Escape se ejecutó al guardar después"
