"""H03: cambios pendientes de Rumbo protegidos (spec 044 T6)."""

from playwright.sync_api import expect


def _open_rumbo(page, server):
    page.goto(server + "/rumbo")
    page.wait_for_function("document.body.dataset.appReady === '1'")
    page.wait_for_selector("#rumbo-hoy", timeout=5000)


def test_h03_rumbo_dia_nav_pide_decision(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("6")
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    # La navegación queda retenida mientras el modal está abierto.
    assert "/rumbo" in page.url
    # Descartar → navega al Dashboard.
    page.locator("#confirm-cancel").click()
    page.wait_for_selector("#dashboard-catalog", timeout=5000)
    assert page.url.rstrip("/").endswith(":8000") or "/" in page.url


def test_h03_rumbo_nombres_nav_guarda_y_limpia(page, server, server_db_path):
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("Pendiente H03")
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    # Guardar → persiste y navega al Dashboard.
    page.locator("#confirm-save").click()
    page.wait_for_selector("#dashboard-catalog", timeout=8000)
    conn = sqlite3.connect(str(server_db_path))
    try:
        row = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert row is not None and row[0] == "Pendiente H03", row


def test_h03_rumbo_sin_cambios_navega_directo(page, server):
    _open_rumbo(page, server)
    page.locator('.workspace-nav a[href="/"]').click()
    page.wait_for_selector("#dashboard-catalog", timeout=5000)
    assert page.locator("#confirm-modal").is_hidden()


def test_h03_rumbo_recarga_con_pendientes_confirma(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("6")
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    page.evaluate("window.location.reload()")
    page.wait_for_timeout(500)
    assert dialogs, "no se mostró confirmación beforeunload con cambios pendientes"
    page.wait_for_function("document.body.dataset.appReady === '1'")


def test_h03_rumbo_tras_guardar_no_pide(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t2").fill("7")
    page.locator("#rumbo-t3").fill("9")
    page.locator('#rumbo-hoy button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.dismiss()))
    page.evaluate("window.location.reload()")
    page.wait_for_timeout(500)
    assert not dialogs, "advertencia innecesaria tras guardar correctamente"
    page.wait_for_function("document.body.dataset.appReady === '1'")


def test_h03_rumbo_dialog_cerrar_con_texto_pide_decision(page, server):
    _open_rumbo(page, server)
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("borrador sin guardar H03")
    page.locator('#rumbo-pregunta-dialog [data-action="close-rumbo-dialog"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    # Descartar → cierra el diálogo de pregunta.
    page.locator("#confirm-cancel").click()
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()


# --- Regresiones revisión 2026-10-03 (R1: baselines por formulario) ---


def test_r1_guardar_dia_mantiene_nombres_pendientes(page, server, server_db_path):
    import datetime
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("NO GUARDADO R1")
    page.locator("#rumbo-t1").fill("8")
    page.locator('#rumbo-hoy button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    # El día sí se guardó…
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        dia = conn.execute("SELECT t1 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert dia is not None and dia[0] == 8, dia
    assert yo is None, yo
    # …pero los nombres siguen protegidos: salir pide decisión.
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    assert "/rumbo" in page.url


def test_r1_guardar_nombres_mantiene_dia_pendiente(page, server, server_db_path):
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("8")
    page.locator("#rumbo-t1-nombre").fill("GUARDADO R1")
    page.locator('#rumbo-yo button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    conn = sqlite3.connect(str(server_db_path))
    try:
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert yo is not None and yo[0] == "GUARDADO R1", yo
    # El día sigue pendiente aunque los nombres ya estén guardados.
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    assert "/rumbo" in page.url


def test_r1_salir_con_fallo_en_nombres_no_navega(page, server, server_db_path):
    import datetime
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("NOMBRES CON FALLO")
    page.locator("#rumbo-t1").fill("8")
    page.route("**/rumbo/yo", lambda r: r.fulfill(status=500, body="Fallo nombres"))
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.locator("#confirm-save").click()
    page.wait_for_timeout(1800)
    page.unroute("**/rumbo/yo")
    # Éxito parcial: el día se guardó, los nombres no, y NO se navegó.
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        dia = conn.execute("SELECT t1 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert dia is not None and dia[0] == 8, dia
    assert yo is None, yo
    assert page.url.endswith("/rumbo"), page.url
    expect(page.locator("#rumbo-t1-nombre")).to_have_value("NOMBRES CON FALLO")


def test_r1_salir_con_fallo_en_dia_no_navega(page, server, server_db_path):
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("NOMBRES OK R1")
    page.locator("#rumbo-t1").fill("8")
    page.route("**/rumbo/dia", lambda r: r.fulfill(status=500, body="Fallo día"))
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.locator("#confirm-save").click()
    page.wait_for_timeout(1800)
    page.unroute("**/rumbo/dia")
    # Orden invertido: falló el día, los nombres sí se guardaron, sin navegar.
    conn = sqlite3.connect(str(server_db_path))
    try:
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert yo is not None and yo[0] == "NOMBRES OK R1", yo
    assert page.url.endswith("/rumbo"), page.url
    expect(page.locator("#rumbo-t1")).to_have_value("8")


def test_r1_respuesta_guardada_mantiene_dia_pendiente(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1").fill("6")
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("borrador R1 con día pendiente")
    page.locator('#rumbo-pregunta-dialog [data-action="close-rumbo-dialog"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    # Guardar solo resuelve la respuesta; el día sigue pendiente.
    page.locator("#confirm-save").click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    expect(page.locator("#rumbo-pregunta-dialog")).not_to_be_visible()
    expect(page.locator("#rumbo-t1")).to_have_value("6")
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    assert "/rumbo" in page.url


# --- Regresiones revisión 2026-10-03 (R2: Escape anula la intención) ---


def test_r2_escape_anula_salida_guardar_normal_no_navega(page, server):
    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("GUARDAR QUEDÁNDOME")
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.keyboard.press("Escape")
    expect(page.locator("#confirm-modal")).not_to_be_visible()
    # Guardado normal posterior: ya no hay destino pendiente.
    page.locator('#rumbo-yo button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(800)
    assert page.url.endswith("/rumbo"), page.url


def test_r2_escape_anula_cambio_pregunta(page, server):
    _open_rumbo(page, server)
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("borrador R2 cambio pregunta")
    page.locator("#rumbo-pregunta-dialog nav button").first.click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.keyboard.press("Escape")
    expect(page.locator("#confirm-modal")).not_to_be_visible()
    # Guardar la respuesta no debe ejecutar el cambio de pregunta cancelado.
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(500)
    expect(page.locator("#rumbo-pregunta-body")).to_contain_text("insatisfacción")


# --- Regresiones revisión 2026-10-03b (R3: coordinar peticiones en vuelo) ---
# Las rutas se retienen (sin responder) y se liberan a mano: determinista,
# sin sleeps dentro de los handlers (bloquearían el dispatcher).


def test_r3_edicion_durante_espera_con_fallo_tardio_no_navega(page, server, server_db_path):
    import datetime
    import sqlite3

    _open_rumbo(page, server)
    inicial = page.locator("#rumbo-t1-nombre").input_value()
    page.locator("#rumbo-t1-nombre").fill("NOMBRE R3 EN VUELO")
    page.locator("#rumbo-t1").fill("8")
    retenidas = {}
    page.route("**/rumbo/dia", lambda r: retenidas.setdefault("dia", r))
    page.route("**/rumbo/yo", lambda r: retenidas.setdefault("yo", r))
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.locator("#confirm-save").click()
    # Ambas peticiones participantes quedan en vuelo…
    for _ in range(50):
        if len(retenidas) == 2:
            break
        page.wait_for_timeout(100)
    assert len(retenidas) == 2, retenidas.keys()
    # …y durante la espera el nombre vuelve a su valor inicial.
    page.locator("#rumbo-t1-nombre").fill(inicial)
    # El día termina con éxito mientras nombres sigue pendiente: sin salida.
    retenidas["dia"].continue_()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    assert page.url.endswith("/rumbo"), page.url
    # El fallo tardío de nombres tampoco navega y conserva el borrador.
    retenidas["yo"].fulfill(status=500, body="Fallo tardío nombres")
    page.wait_for_selector("#notice-container .notice-error", timeout=5000)
    page.wait_for_timeout(400)
    assert page.url.endswith("/rumbo"), page.url
    expect(page.locator("#rumbo-t1-nombre")).to_have_value(inicial)
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        dia = conn.execute("SELECT t1 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert dia is not None and dia[0] == 8, dia
    assert yo is None, yo


def test_r3_guardar_y_salir_espera_todos_los_guardados(page, server, server_db_path):
    import datetime
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("NOMBRES R3 COORDINADO")
    page.locator("#rumbo-t1").fill("8")
    retenidas = {}
    page.route("**/rumbo/dia", lambda r: retenidas.setdefault("dia", r))
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.locator("#confirm-save").click()
    # Nombres vuela y termina; el día sigue retenido: todavía sin salida.
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    assert page.url.endswith("/rumbo"), page.url
    assert "dia" in retenidas, "el guardado del día debió quedar retenido"
    # Al liberar el día, ambos persisten y entonces sí se navega.
    retenidas["dia"].continue_()
    page.wait_for_selector("#dashboard-catalog", timeout=8000)
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        dia = conn.execute("SELECT t1 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert dia is not None and dia[0] == 8, dia
    assert yo is not None and yo[0] == "NOMBRES R3 COORDINADO", yo


# --- Regresiones revisión 2026-10-03c (P1: borrador posterior al envío) ---


def test_r3b_edicion_media_nombres_no_se_pierde(page, server, server_db_path):
    import datetime
    import sqlite3

    _open_rumbo(page, server)
    page.locator("#rumbo-t1-nombre").fill("NOMBRE R3B ENVIADO")
    page.locator("#rumbo-t1").fill("8")
    retenidas = {}
    page.route("**/rumbo/dia", lambda r: retenidas.setdefault("dia", r))
    page.route("**/rumbo/yo", lambda r: retenidas.setdefault("yo", r))
    page.locator('.workspace-nav a[href="/"]').click()
    expect(page.locator("#confirm-modal")).to_be_visible(timeout=3000)
    page.locator("#confirm-save").click()
    for _ in range(50):
        if len(retenidas) == 2:
            break
        page.wait_for_timeout(100)
    assert len(retenidas) == 2, retenidas.keys()
    # Edición posterior mientras ambas siguen en vuelo.
    page.locator("#rumbo-t1-nombre").fill("NOMBRE R3B POSTERIOR")
    retenidas["dia"].continue_()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    # El borrador posterior se conserva (no lo pisa el swap OOB) y no se sale.
    expect(page.locator("#rumbo-t1-nombre")).to_have_value("NOMBRE R3B POSTERIOR")
    assert page.url.endswith("/rumbo"), page.url
    retenidas["yo"].continue_()
    page.wait_for_timeout(800)
    # Tras ambos éxitos el borrador posterior sigue pendiente: sin salida.
    expect(page.locator("#rumbo-t1-nombre")).to_have_value("NOMBRE R3B POSTERIOR")
    assert page.url.endswith("/rumbo"), page.url
    # La DB conserva la versión enviada, no la posterior.
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(server_db_path))
    try:
        dia = conn.execute("SELECT t1 FROM rumbo_dia WHERE fecha = ?", (hoy,)).fetchone()
        yo = conn.execute("SELECT t1_nombre FROM rumbo_yo").fetchone()
    finally:
        conn.close()
    assert dia is not None and dia[0] == 8, dia
    assert yo is not None and yo[0] == "NOMBRE R3B ENVIADO", yo


def test_r3b_respuesta_posterior_no_cierra_dialogo(page, server, server_db_path):
    import sqlite3

    _open_rumbo(page, server)
    page.click('#rumbo-preguntas button:has-text("Insatisfacción tolerada")')
    page.wait_for_selector("#rumbo-pregunta-dialog[open]", timeout=5000)
    page.click("#rumbo-pregunta-dialog .rumbo-nueva summary")
    page.locator("#rumbo-respuesta-texto").fill("borrador R3B enviado")
    retenidas = {}
    page.route("**/rumbo/respuesta", lambda r: retenidas.setdefault("resp", r))
    page.locator('#rumbo-pregunta-dialog button[type="submit"]').click()
    for _ in range(50):
        if len(retenidas) == 1:
            break
        page.wait_for_timeout(100)
    assert len(retenidas) == 1, retenidas.keys()
    # Se sigue escribiendo mientras se guarda.
    page.locator("#rumbo-respuesta-texto").fill("borrador R3B posterior")
    retenidas["resp"].continue_()
    page.wait_for_selector("#notice-container .notice-success", timeout=5000)
    page.wait_for_timeout(400)
    # El éxito no cierra el diálogo con borrador posterior pendiente.
    expect(page.locator("#rumbo-pregunta-dialog[open]")).to_be_visible()
    expect(page.locator("#rumbo-respuesta-texto")).to_have_value("borrador R3B posterior")
    # El servidor guardó la versión enviada.
    conn = sqlite3.connect(str(server_db_path))
    try:
        ultima = conn.execute(
            "SELECT respuesta FROM rumbo_respuestas ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert ultima is not None and ultima[0] == "borrador R3B enviado", ultima
