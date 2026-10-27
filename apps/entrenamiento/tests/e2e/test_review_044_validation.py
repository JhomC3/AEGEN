"""Error de validación HTTP sin fragmento de aviso OOB."""

from playwright.sync_api import expect


def test_review_empty_response_has_visible_feedback(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady==='1'")
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]")
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("")
    with page.expect_response(lambda r: r.url.endswith("/rumbo/respuesta")) as result:
        page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    assert result.value.status == 422
    page.screenshot(path=".tmp/review/p2-empty-422.png")
    expect(page.locator("#rumbo-pregunta-dialog")).to_be_visible()
    expect(page.locator("#rumbo-respuesta-notice [role=alert]")).to_be_visible(timeout=1500)
    # El diálogo sigue abierto y el reintento con contenido guarda y cierra.
    page.locator("#rumbo-respuesta-texto").fill("respuesta válida tras 422")
    page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()


def test_review_stale_success_not_reused_for_empty_response(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady==='1'")
    page.locator("#rumbo-t1-nombre").fill("Nombre para comprobar aviso")
    page.locator("#rumbo-yo button[type=submit]").click()
    expect(page.locator("#notice-container .notice-success")).to_be_visible()
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]")
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    expect(page.locator("#notice-container .notice-success")).to_be_attached()
    page.locator("#rumbo-respuesta-texto").fill("")
    with page.expect_response(lambda r: r.url.endswith("/rumbo/respuesta")) as result:
        page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    assert result.value.status == 422
    # El aviso local comunica error, no reutiliza el éxito anterior.
    aviso = page.locator("#rumbo-respuesta-notice .notice-error")
    expect(aviso).to_be_visible(timeout=1500)
    expect(aviso).to_contain_text("No se pudo guardar")
    expect(aviso).not_to_contain_text("Rumbo guardado")
    # Reintento válido guarda y cierra.
    page.locator("#rumbo-respuesta-texto").fill("respuesta válida tras aviso rancio")
    page.locator("#rumbo-pregunta-dialog button[type=submit]").click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()
