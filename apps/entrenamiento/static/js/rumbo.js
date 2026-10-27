// rumbo.js — eco local de sliders + popup de preguntas (mejora progresiva).
// El score y la verdad siempre viven en el servidor.
// Spec 044 H03: baseline de día/nombres/respuesta para proteger cambios
// pendientes (salida de página, navegación principal y cierre del diálogo)
// reutilizando #confirm-modal y htmx-lifecycle (sin sistema paralelo).

import { closeDialog, openDialog } from './modal-dialog.js';
import { hideConfirmDialog, showConfirmDialog } from './state.js';

let diaBaseline = null;
let nombresBaseline = null;
let respuestaBaseline = null;
let pendingHref = null;
let pendingPregunta = null;
// R3: guardados en vuelo; la salida espera cola vacía y cero cambios.
let inFlightRumboSaves = new Set();
// H04: los envíos nacen `disabled` y solo JS los habilita; cada re-render
// OOB los devuelve a `disabled`, así que se rehabilitan tras cada swap
// (salvo vuelo en curso, para no romper el anti-doble-submit).
function enableRumboSubmits() {
    const pairs = [
        [diaForm(), "/rumbo/dia"],
        [nombresForm(), "/rumbo/yo"],
        [respuestaForm(), "/rumbo/respuesta"],
    ];
    pairs.forEach(([form, path]) => {
        if (!form || inFlightRumboSaves.has(path)) return;
        form.querySelectorAll('button[type="submit"]').forEach((btn) => {
            btn.disabled = false;
        });
    });
}
// P1 (revisión 2026-10-03c): versión enviada frente a borrador posterior.
// El swap OOB re-renderiza con lo guardado y borraría ediciones en espera:
// se restauran y no se navega ni se cierra el diálogo.
let submittedDia = null;
let submittedNombres = null;
let submittedRespuesta = null;
let draftDia = null;
let draftNombres = null;
let draftRespuesta = null;

function rumboRequestPath(e) {
    const cfg = (e.detail && e.detail.requestConfig) || {};
    return cfg.path
        || (e.detail && e.detail.pathInfo && e.detail.pathInfo.requestPath)
        || "";
}

function isRumboSavePath(path) {
    return path === "/rumbo/dia" || path === "/rumbo/yo" || path === "/rumbo/respuesta";
}

function diaForm() {
    return document.querySelector('#rumbo-hoy form.rumbo-form');
}

function nombresForm() {
    return document.querySelector('#rumbo-yo form.rumbo-form');
}

function respuestaForm() {
    const dialog = document.getElementById('rumbo-pregunta-dialog');
    if (!dialog || !dialog.open) return null;
    return dialog.querySelector('form.rumbo-form');
}

function respuestaTextarea() {
    const form = respuestaForm();
    return form ? form.querySelector('textarea[name="respuesta"]') : null;
}

function serializeDia(form) {
    form = form || diaForm();
    if (!form) return null;
    const vals = Array.from(
        form.querySelectorAll('input[data-rumbo-slider][type="range"]')
    ).map((el) => el.value);
    const fecha = form.querySelector('input[name="fecha"]');
    return JSON.stringify({ fecha: fecha ? fecha.value : '', vals });
}

function serializeNombres(form) {
    form = form || nombresForm();
    if (!form) return null;
    const vals = Array.from(form.querySelectorAll('input[name]')).map(
        (el) => el.name + '=' + el.value
    );
    return JSON.stringify(vals);
}

function serializeRespuesta(area) {
    area = area || respuestaTextarea();
    if (!area) return null;
    return area.value;
}

function captureDiaBaseline() {
    const dia = serializeDia();
    if (dia !== null) diaBaseline = dia;
    if (dia !== null) draftDia = dia;
    submittedDia = null;
}

function captureNombresBaseline() {
    const nom = serializeNombres();
    if (nom !== null) nombresBaseline = nom;
    if (nom !== null) draftNombres = nom;
    submittedNombres = null;
}

function captureRespuestaBaseline() {
    const resp = serializeRespuesta();
    if (resp !== null) respuestaBaseline = resp;
    if (resp !== null) draftRespuesta = resp;
    submittedRespuesta = null;
}

function captureRumboBaselines() {
    captureDiaBaseline();
    captureNombresBaseline();
    captureRespuestaBaseline();
}

/* Anula una intención de salida pendiente (Escape en la confirmación):
   solo un descartar explícito autoriza la navegación. */
function cancelRumboPending() {
    pendingHref = null;
    pendingPregunta = null;
}

export function rumboIsDirty() {
    const root = document.getElementById('main-content');
    if (!root || !root.classList.contains('rumbo-page')) return false;
    const dia = serializeDia();
    if (dia !== null && diaBaseline !== null && dia !== diaBaseline) return true;
    const nom = serializeNombres();
    if (nom !== null && nombresBaseline !== null && nom !== nombresBaseline) return true;
    const resp = serializeRespuesta();
    if (resp !== null && respuestaBaseline !== null && resp !== respuestaBaseline) return true;
    return false;
}

function respuestaIsDirty() {
    const resp = serializeRespuesta();
    return resp !== null && respuestaBaseline !== null && resp !== respuestaBaseline;
}

function submitDirtyRumboForms() {
    const dia = serializeDia();
    if (dia !== null && diaBaseline !== null && dia !== diaBaseline) {
        diaForm().requestSubmit();
    }
    const nom = serializeNombres();
    if (nom !== null && nombresBaseline !== null && nom !== nombresBaseline) {
        nombresForm().requestSubmit();
    }
    if (respuestaIsDirty()) {
        const form = respuestaForm();
        if (form) form.requestSubmit();
    }
}

/* Borrador posterior (P1): lo tecleado durante la espera sobrevive al swap
   OOB re-aplicándolo tras el éxito; la base queda en la versión enviada. */
function trackRumboDraft(target) {
    // Se serializa el propio formulario del evento: durante un swap OOB
    // puede haber un duplicado transitorio con valores ya guardados.
    // (El blur/change de nodos desmontados se ignora por isConnected.)
    if (!(target instanceof HTMLElement) || !target.closest || !target.isConnected) return;
    const scopeForm = target.closest("form.rumbo-form");
    if (!scopeForm) return;
    if (scopeForm.closest("#rumbo-hoy")) draftDia = serializeDia(scopeForm);
    else if (scopeForm.closest("#rumbo-yo")) draftNombres = serializeNombres(scopeForm);
    else if (scopeForm.closest("#rumbo-pregunta-dialog")) {
        const area = scopeForm.querySelector('textarea[name="respuesta"]');
        if (area) draftRespuesta = serializeRespuesta(area);
    }
}

function restoreDiaDraft() {
    const form = diaForm();
    if (!form || draftDia === null) return;
    let vals = null;
    try {
        vals = JSON.parse(draftDia).vals;
    } catch (err) {
        return;
    }
    if (!Array.isArray(vals)) return;
    form.querySelectorAll('input[data-rumbo-slider][type="range"]').forEach((el, i) => {
        if (vals[i] === undefined) return;
        el.value = vals[i];
        syncRow(el);
    });
    syncTotal(document.getElementById("main-content"));
}

function restoreNombresDraft() {
    const form = nombresForm();
    if (!form || draftNombres === null) return;
    let pairs = null;
    try {
        pairs = JSON.parse(draftNombres);
    } catch (err) {
        return;
    }
    if (!Array.isArray(pairs)) return;
    pairs.forEach((p) => {
        const cut = String(p).indexOf("=");
        if (cut < 0) return;
        const input = form.querySelector('input[name="' + CSS.escape(String(p).slice(0, cut)) + '"]');
        if (input) input.value = String(p).slice(cut + 1);
    });
}

function askRumboConfirm(onSave, onDiscard) {
    const msg = document.getElementById('confirm-msg');
    if (msg) msg.textContent = 'Tienes cambios sin guardar en Rumbo. ¿Guardar antes de salir?';
    showConfirmDialog(onSave, onDiscard);
}

function goPendingHref() {
    const href = pendingHref;
    pendingHref = null;
    if (href) window.location.assign(href);
}

function goPendingPregunta() {
    const req = pendingPregunta;
    pendingPregunta = null;
    if (req) {
        htmx.ajax('GET', req.path, { target: '#rumbo-pregunta-body', swap: 'innerHTML' });
    }
}

function syncRow(input) {
    const out = input.parentElement.querySelector("output.rumbo-num");
    if (out) out.textContent = input.value;
}

function syncTotal(root) {
    const hoy = root.querySelector("#rumbo-hoy");
    if (!hoy) return;
    const inputs = hoy.querySelectorAll('input[data-rumbo-slider][type="range"]');
    if (inputs.length !== 3) return;
    let total = 0;
    inputs.forEach((el) => {
        total += Number(el.value) || 0;
    });
    // Spec 044 H05: el borrador vive en su propio nodo y nunca pisa el
    // guardado. Se oculta cuando coincide con lo guardado.
    const borrador = hoy.querySelector(".rumbo-borrador");
    const guardadoEl = hoy.querySelector(".rumbo-guardado");
    if (borrador && guardadoEl) {
        const num = borrador.querySelector(".rumbo-num");
        if (num) num.textContent = `${total}/30`;
        const g = guardadoEl.dataset.guardado;
        borrador.hidden = (g !== "" && Number(g) === total);
        return;
    }
    // Fallback pre-H05 (sin nodos distinguidos): eco directo legacy.
    const h2 = hoy.querySelector(".panel-title .rumbo-num");
    if (h2) h2.textContent = `${total}/30`;
}

export function initRumbo() {
    const root = document.getElementById("main-content");
    if (!root || !root.classList.contains("rumbo-page")) return;
    if (root.dataset.rumboReady === "1") return;
    root.dataset.rumboReady = "1";
    captureRumboBaselines();
    root.addEventListener("input", (e) => {
        const el = e.target;
        if (el instanceof HTMLInputElement
            && el.matches('#rumbo-hoy input[data-rumbo-slider][type="range"]')) {
            syncRow(el);
            syncTotal(root);
        }
        trackRumboDraft(el);
    });
    root.addEventListener("change", (e) => {
        trackRumboDraft(e.target);
    });
    // Cierre del diálogo con cambios: pide decisión (guardar/descartar).
    root.addEventListener("click", (e) => {
        const el = e.target.closest("[data-action]");
        if (!el) return;
        if (el.dataset.action === "close-rumbo-dialog") {
            if (respuestaIsDirty()) {
                e.preventDefault();
                askRumboConfirm(
                    function () { submitDirtyRumboForms(); },
                    function () {
                        const area = respuestaTextarea();
                        if (area && respuestaBaseline !== null) area.value = respuestaBaseline;
                        closeDialog(el.closest("dialog"));
                    }
                );
                return;
            }
            e.preventDefault();
            closeDialog(el.closest("dialog"));
        }
    });
    // Navegación entre preguntas con respuesta a medio escribir: retiene el
    // swap htmx (fase de captura, antes que la delegación de htmx) y pide
    // decisión; al descartar re-emite la petición manualmente.
    root.addEventListener(
        "click",
        (e) => {
            const btn = e.target.closest(".rumbo-pregunta-nav button[hx-get]");
            if (!btn || !respuestaIsDirty()) return;
            e.preventDefault();
            e.stopPropagation();
            pendingPregunta = { path: btn.getAttribute("hx-get") };
            askRumboConfirm(
                function () { submitDirtyRumboForms(); },
                function () { goPendingPregunta(); }
            );
        },
        true
    );
    // Salida por la navegación principal con pendientes: retiene el enlace.
    root.addEventListener("click", (e) => {
        const link = e.target.closest(".workspace-nav a[href]");
        if (!link || !rumboIsDirty()) return;
        e.preventDefault();
        pendingHref = link.getAttribute("href");
        askRumboConfirm(
            function () { submitDirtyRumboForms(); },
            function () { goPendingHref(); }
        );
    });
    // Escape en el diálogo con cambios: retiene el cierre nativo.
    const dialog = document.getElementById("rumbo-pregunta-dialog");
    if (dialog) {
        dialog.addEventListener("cancel", (e) => {
            if (!respuestaIsDirty()) return;
            e.preventDefault();
            askRumboConfirm(
                function () { submitDirtyRumboForms(); },
                function () {
                    const area = respuestaTextarea();
                    if (area && respuestaBaseline !== null) area.value = respuestaBaseline;
                    closeDialog(dialog);
                }
            );
        });
    }
    document.body.addEventListener("htmx:afterSwap", (e) => {
        if (e.detail && e.detail.target && e.detail.target.id === "rumbo-pregunta-body") {
            openDialog(document.getElementById("rumbo-pregunta-dialog"));
            const resp = serializeRespuesta();
            if (resp !== null) respuestaBaseline = resp;
            enableRumboSubmits();
        }
    });
    // H04: cualquier re-render OOB (guardado, undo, navegación de pregunta)
    // devuelve botones `disabled`: se rehabilitan salvo vuelo en curso.
    document.body.addEventListener("htmx:oobAfterSwap", (e) => {
        const target = e.detail && e.detail.target;
        if (!target || !target.id) return;
        if (target.id === "rumbo-hoy" || target.id === "rumbo-yo"
            || target.id === "rumbo-pregunta-body") {
            enableRumboSubmits();
        }
    });
    document.body.addEventListener("htmx:afterRequest", (e) => {
        const path = rumboRequestPath(e);
        if (!e.detail || !isRumboSavePath(path)) return;
        inFlightRumboSaves.delete(path);
        if (!e.detail.successful) {
            // Fallo: se mantiene página, aviso y borradores; la salida
            // pendiente se anula (sin navegación posterior implícita).
            cancelRumboPending();
            return;
        }
        // R1: cada éxito solo confirma su propio formulario; los demás
        // siguen pendientes. P1: si hubo edición posterior al envío, se
        // restaura el borrador, la base queda en la versión enviada y no
        // se sale ni se cierra el diálogo.
        if (path === "/rumbo/dia") {
            if (submittedDia !== null && draftDia !== null && draftDia !== submittedDia) {
                restoreDiaDraft();
                diaBaseline = submittedDia;
                submittedDia = null;
            } else {
                captureDiaBaseline();
            }
        } else if (path === "/rumbo/yo") {
            if (submittedNombres !== null && draftNombres !== null && draftNombres !== submittedNombres) {
                restoreNombresDraft();
                nombresBaseline = submittedNombres;
                submittedNombres = null;
            } else {
                captureNombresBaseline();
            }
        } else if (path === "/rumbo/respuesta") {
            if (submittedRespuesta !== null && draftRespuesta !== null
                && draftRespuesta !== submittedRespuesta) {
                respuestaBaseline = submittedRespuesta;
                submittedRespuesta = null;
            } else {
                closeDialog(document.getElementById("rumbo-pregunta-dialog"));
                captureRespuestaBaseline();
            }
        }
        // R3: salir solo sin guardados en vuelo ni cambios posteriores.
        // El formulario recién terminado se rehabilita ya (los demás en
        // vuelo siguen protegidos por el anti-doble-submit).
        enableRumboSubmits();
        if (inFlightRumboSaves.size > 0) return;
        if (path === "/rumbo/respuesta") {
            if (pendingPregunta && !respuestaIsDirty()) goPendingPregunta();
            else if (pendingHref && !rumboIsDirty()) goPendingHref();
        } else if (pendingHref && !rumboIsDirty()) {
            goPendingHref();
        }
    });
    // R3: contar cada guardado emitido.
    document.body.addEventListener("htmx:beforeRequest", (e) => {
        const path = rumboRequestPath(e);
        if (!isRumboSavePath(path)) return;
        inFlightRumboSaves.add(path);
        // P1: la foto es la versión enviada (misma tarea que el submit, sin
        // carrera con tecleado posterior).
        if (path === "/rumbo/dia") submittedDia = draftDia !== null ? draftDia : serializeDia();
        else if (path === "/rumbo/yo") {
            submittedNombres = draftNombres !== null ? draftNombres : serializeNombres();
        } else if (path === "/rumbo/respuesta") {
            submittedRespuesta = draftRespuesta !== null ? draftRespuesta : serializeRespuesta();
        }
    });
    // R2: Escape en la confirmación anula la intención pendiente (destino +
    // callbacks); no debe ejecutarse en un guardado posterior.
    const confirmModal = document.getElementById("confirm-modal");
    if (confirmModal) {
        confirmModal.addEventListener("cancel", function () {
            cancelRumboPending();
            hideConfirmDialog();
        });
    }
    // H04: los envíos nacen `disabled`; con JS se habilitan al cargar.
    enableRumboSubmits();
}
