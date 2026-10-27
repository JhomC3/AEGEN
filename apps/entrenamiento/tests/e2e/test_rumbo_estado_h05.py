"""H05: encabezado distingue guardado y borrador (spec 044 T8)."""

from playwright.sync_api import expect


def _open_rumbo(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)


def test_h05_sin_registro_explicito_y_rango_sliders(page, server):
    _open_rumbo(page, server)
    expect(page.locator("#rumbo-hoy .rumbo-guardado")).to_contain_text("Sin registro")
    # Borrador inicial 5+5+5 = 15/30, visible junto al Sin registro.
    expect(page.locator("#rumbo-hoy .rumbo-borrador")).to_be_visible()
    expect(page.locator("#rumbo-hoy .rumbo-borrador")).to_contain_text("15/30")
    # Rango contratado intacto.
    for sel in ("#rumbo-t1", "#rumbo-t2", "#rumbo-t3"):
        expect(page.locator(sel)).to_have_attribute("min", "1")
        expect(page.locator(sel)).to_have_attribute("max", "10")
        expect(page.locator(sel)).to_have_value("5")


def test_h05_borrador_no_pisa_guardado(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("6")
    expect(page.locator("#rumbo-hoy .rumbo-borrador")).to_contain_text("16/30")
    # El estado guardado sigue diciendo Sin registro.
    expect(page.locator("#rumbo-hoy .rumbo-guardado")).to_contain_text("Sin registro")


def test_h05_guardar_muestra_guardado_y_recarga_persiste(page, server, server_db_path):
    import sqlite3
    from datetime import date

    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t2").fill("7")
    page.locator("#rumbo-t3").fill("9")
    page.locator('#rumbo-hoy button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-hoy .rumbo-guardado")).to_contain_text("24/30")
    # Borrador coincide con lo guardado: no se muestra duplicado.
    assert not page.locator("#rumbo-hoy .rumbo-borrador").is_visible()
    # Mover un slider tras guardar: reaparece el borrador sin tocar el guardado.
    page.locator("#rumbo-t1").fill("9")
    expect(page.locator("#rumbo-hoy .rumbo-borrador")).to_be_visible()
    expect(page.locator("#rumbo-hoy .rumbo-borrador")).to_contain_text("25/30")
    expect(page.locator("#rumbo-hoy .rumbo-guardado")).to_contain_text("24/30")
    # Persistencia real tras recarga.
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    expect(page.locator("#rumbo-hoy .rumbo-guardado")).to_contain_text("24/30")
    hoy = date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        row = conn.execute("SELECT t1, t2, t3 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
    finally:
        conn.close()
    assert row == (8, 7, 9), row
