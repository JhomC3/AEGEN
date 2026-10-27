// htmx-lifecycle.js — owns: delegated htmx:* handlers and document-level events.
// It calls module initializers instead of duplicating their logic.
// Public API: initLifecycle.

import { doNav, updateDateDot } from './date-navigation.js';
import {
    handleEditorState,
    initEditorRowSortable,
    recalcRM,
    syncEditButtons,
    syncEditorFromContent,
    updateEditActions,
} from './editor.js';
import { scheduleNotices } from './notices.js';
import {
    initNutritionRowSortable,
    syncNutritionSortableState,
} from './row-sortable.js';
import {
    ensureNutritionEditable,
    nutritionIsDirty,
    refreshNutritionEditor,
    refreshNutritionRowsOrder,
} from './nutrition-editor.js';
import { refreshNutritionTemplatesDnD } from './nutrition-templates.js';
import {
    confirmEntrenoSave,
    guardarPlantillaToggle,
    initEntrenoDnD,
    initTemplateSortable,
    syncTemplateEjercicios,
} from './templates.js';
import {
    editorEditmode,
    getConfirmCbs,
    getPendingNav,
    getPlantillaAppliedPending,
    getSaveRequested,
    hideConfirmDialog,
    isDirty,
    noteFieldEdit,
    noteFormFocus,
    popFieldEdit,
    setPendingNav,
    setPlantillaAppliedPending,
    setSaveRequested,
} from './state.js';
import { rumboIsDirty } from './rumbo.js';

function dailyVista() {
    const page = document.getElementById('daily-page');
    return page ? (page.dataset.vista || 'entrenamiento') : null;
}

function shouldUpdateDot(kindVista) {
    const vista = dailyVista();
    // Fuera del Diario (popup del Dashboard): solo puntos de entrenamiento.
    if (vista === null) return kindVista === 'entrenamiento';
    return vista === kindVista;
}

function undoKindToVista(kind) {
    if (kind === 'sesion') return 'entrenamiento';
    if (kind === 'alimentacion') return 'alimentacion';
    return null;
}

// R4: error dentro del diálogo abierto (el global queda tras el backdrop).
function rumboNoticeContainer(saveForm) {
    const dialog = saveForm.closest ? saveForm.closest('dialog') : null;
    if (dialog && dialog.open) {
        const local = dialog.querySelector('#rumbo-respuesta-notice');
        if (local) return local;
    }
    return document.getElementById('notice-container');
}

// P2: traslada al diálogo el aviso de ERROR OOB que el servidor dejó en el
// contenedor global (solo formularios dentro de un modal abierto). Nunca se
// reutiliza un éxito anterior: sin error propio se sintetiza el respaldo.
// Devuelve si mostró algo en el diálogo.
function mirrorNoticeIntoDialog(saveForm) {
    const dialog = saveForm.closest ? saveForm.closest('dialog') : null;
    if (!dialog || !dialog.open) return false;
    const local = dialog.querySelector('#rumbo-respuesta-notice');
    if (!local) return false;
    const container = document.getElementById('notice-container');
    const globalNotice = container && container.querySelector('.notice-error');
    local.innerHTML = '';
    if (globalNotice) {
        local.appendChild(globalNotice);
    } else {
        local.innerHTML =
            '<div class="notice notice-error" data-dismiss="4500" role="alert">' +
            'No se pudo guardar. Revisa el contenido e inténtalo de nuevo.</div>';
    }
    scheduleNotices();
    return true;
}

export function initLifecycle() {
    document.getElementById('confirm-cancel').addEventListener('click', function () {
        const cbs = getConfirmCbs();
        hideConfirmDialog();
        if (cbs && cbs.onDiscard) cbs.onDiscard();
    });
    document.getElementById('confirm-save').addEventListener('click', function () {
        const cbs = getConfirmCbs();
        hideConfirmDialog();
        if (cbs && cbs.onSave) cbs.onSave();
    });

    // htmx descarta el cuerpo de las respuestas 4xx por defecto, lo que impedía
    // que los avisos de error de dominio (validación, CSRF) llegaran al DOM vía OOB.
    // Se permite el swap solo en 4xx (respuestas propias); los 500 internos se
    // mantienen sin renderizar (log de servidor).
    document.body.addEventListener('htmx:beforeSwap', function (e) {
        const xhr = e.detail && e.detail.xhr;
        if (xhr && xhr.status >= 400 && xhr.status < 500) {
            e.detail.shouldSwap = true;
        }
    });

    document.body.addEventListener('htmx:afterSwap', function (e) {
        scheduleNotices();
        handleEditorState();
        if (e.detail && e.detail.target) {
            if (e.detail.target.id === 'session-editor-wrap') {
                syncEditorFromContent();
                if (document.getElementById('plantilla-applied')) {
                    document.getElementById('plantilla-applied').remove();
                    setPlantillaAppliedPending(true);
                }
                initEditorRowSortable();
            } else if (e.detail.target.id === 'popup-body') {
                // Apertura del popup: el editor llega por swap al cuerpo del popup.
                syncEditorFromContent();
                initEditorRowSortable();
                initNutritionRowSortable(refreshNutritionRowsOrder, ensureNutritionEditable);
                // Las plantillas (entrenamiento y alimentación) viven en el popup:
                // re-vincular su DnD tras el swap.
                initTemplateSortable();
                refreshNutritionTemplatesDnD();
            } else if (e.detail.target === document.body && document.getElementById('plantilla-applied')) {
                syncEditorFromContent();
                document.getElementById('plantilla-applied').remove();
                setPlantillaAppliedPending(true);
                initEditorRowSortable();
            } else if (e.detail.target.id === 'plantillas-section') {
                initTemplateSortable();
            }
        }
    });

    document.body.addEventListener('htmx:afterSettle', function (e) {
        if (!getPlantillaAppliedPending()) return;
        const target = e.detail && e.detail.target;
        if (target && (target.id === 'session-editor-wrap' || target === document.body)) {
            setPlantillaAppliedPending(false);
            const editor = document.getElementById('session-editor');
            if (editor) {
                editor.dataset.baseline = '';
                updateEditActions();
            }
        }
    });

    document.body.addEventListener('htmx:afterRequest', function (e) {
        scheduleNotices();
        handleEditorState();
        // Los 5xx y fallos de red no intercambian contenido (beforeSwap solo
        // permite 4xx): el servidor no llega a enviar un aviso OOB. Para que
        // un error interno de guardado nunca sea silencioso, se muestra un
        // aviso genérico en el contenedor del formulario afectado (spec 044
        // H02: incluye los .rumbo-form, que antes quedaban vacíos).
        const elt = e.detail && e.detail.elt;
        const saveForm = elt && elt.closest
            ? elt.closest('#session-form, #nutrition-form, .rumbo-form')
            : null;
        if (saveForm && !e.detail.successful) {
            const status = e.detail.xhr ? e.detail.xhr.status : 0;
            if (status === 0 || status >= 400) {
                const container = saveForm.id === 'session-form'
                    ? document.getElementById('editor-notice')
                    : saveForm.id === 'nutrition-form'
                        ? document.getElementById('nutrition-notice') || document.getElementById('notice-container')
                        : rumboNoticeContainer(saveForm);
                if (container) {
                    // Los 400 de dominio ya traen su aviso OOB (beforeSwap
                    // permite 4xx): aquí solo 403/5xx/red para no duplicar.
                    const msg = status === 403
                        ? 'Solicitud no autorizada. Recarga la página e intenta de nuevo.'
                        : status >= 500
                            ? 'Error interno del servidor. Tus cambios no se guardaron.'
                            : status === 0
                                ? 'Sin conexión. Tus cambios no se guardaron. Reintenta.'
                                : '';
                    if (msg) {
                        container.innerHTML =
                            '<div class="notice notice-error" data-dismiss="4500" role="alert">' +
                            msg + '</div>';
                        scheduleNotices();
                    } else if (status >= 400 && status < 500) {
                        // P2: el aviso OOB del servidor (p. ej. 400 de
                        // validación) cayó en el contenedor global, detrás
                        // del backdrop. Se traslada al aviso interno del
                        // diálogo abierto, en una sola copia.
                        mirrorNoticeIntoDialog(saveForm);
                    }
                }
            }
        }
        initTemplateSortable();
        initEntrenoDnD();
        const ptForm = e.detail && e.detail.elt && e.detail.elt.closest
            ? e.detail.elt.closest('#save-template-form')
            : null;
        if (ptForm && e.detail.successful) {
            guardarPlantillaToggle(false);
        }
        // El editor nutricional solo se re-baselinea cuando LA RESPUESTA lo
        // toca (save/delete/nav/undo de nutrición): hacerlo en cada request
        // (p. ej. guardar sesión) descartaba cambios de alimentación sin guardar.
        if (e.detail.successful && document.getElementById('nutrition-form')
            && responseUpdatesNutrition(e)) {
            refreshNutritionEditor();
            initNutritionRowSortable(refreshNutritionRowsOrder, ensureNutritionEditable);
            syncNutritionSortableState();
            // Dot inmediato de alimentación (save/eliminar): solo si la vista
            // activa es alimentación; en entrenamiento el punto no debe cambiar.
            const reqPath = (e.detail.requestConfig && e.detail.requestConfig.path) || '';
            if (reqPath.startsWith('/alimentacion/save') || reqPath.startsWith('/alimentacion/eliminar')) {
                const nForm = document.getElementById('nutrition-form');
                const nFechaInput = nForm && nForm.querySelector('input[name="fecha"]');
                const nFecha = nFechaInput ? nFechaInput.value : '';
                const nSt = document.getElementById('nutrition-editor-state');
                const nHas = nSt && nSt.dataset.hasData !== undefined ? nSt.dataset.hasData === '1' : null;
                if (nFecha && nHas !== null && shouldUpdateDot('alimentacion')) {
                    updateDateDot(nFecha, nHas);
                }
            }
        }
        refreshNutritionTemplatesDnD();
        if (getSaveRequested() && document.getElementById('session-form')) {
            setSaveRequested(false);
            const undoRes = document.getElementById('undo-result');
            if (undoRes && undoRes.dataset.fecha) {
                const undoVista = undoKindToVista(undoRes.dataset.kind || '');
                if (undoVista === null || shouldUpdateDot(undoVista)) {
                    updateDateDot(undoRes.dataset.fecha, undoRes.dataset.hasData === '1');
                }
                undoRes.removeAttribute('data-fecha');
                undoRes.removeAttribute('data-has-data');
                undoRes.removeAttribute('data-kind');
            }
            const outcome = document.getElementById('save-outcome');
            if (e.detail.successful && outcome && outcome.dataset.ok === '1') {
                // Los swaps OOB ya están aplicados en afterRequest: pintamos el
                // dot de inmediato (el navegador puede navegar justo después y
                // el estado debe ser visible sin esperar el setTimeout).
                const form = document.getElementById('session-form');
                const fechaInput = form && form.querySelector('input[name="fecha"]');
                const fecha = fechaInput ? fechaInput.value : '';
                const st = document.getElementById('editor-state');
                const hasData = st && st.dataset.hasData !== undefined ? st.dataset.hasData === '1' : null;
                if (hasData !== null && shouldUpdateDot('entrenamiento')) {
                    updateDateDot(fecha, hasData);
                    syncEditButtons();
                } else if (hasData !== null) {
                    syncEditButtons();
                }
                setTimeout(function () {
                    recalcRM();
                    syncEditorFromContent();
                }, 100);
                if (getPendingNav()) {
                    const target = getPendingNav();
                    setPendingNav(null);
                    setTimeout(function () { doNav(target, true); }, 150);
                }
            } else {
                setPendingNav(null);
            }
        }
    });

    document.addEventListener('submit', function (e) {
        const form = e.target.closest('#session-form');
        if (!form) return;
        if (editorEditmode() !== '1') {
            e.preventDefault();
            return;
        }
        setSaveRequested(true);
    }, true);

    // Estado "Guardando…" y anti doble-submit: mientras la petición htmx del
    // formulario está en vuelo, el botón de guardar se deshabilita y muestra
    // "Guardando…". Se restaura al terminar (éxito o error); tras el swap el
    // syncEditButtons re-evalúa el disabled según el modo del editor. Los
    // .rumbo-form comparten el contrato (spec 044 H02) y siempre se
    // rehabilitan (Rumbo no tiene modo readonly).
    document.body.addEventListener('htmx:beforeRequest', function (e) {
        const elt = e.detail && e.detail.elt;
        if (!elt) return;
        const form = elt.closest('#session-form, #nutrition-form, .rumbo-form');
        if (!form) return;
        // Un nuevo intento supera el feedback anterior: en el diálogo, un
        // aviso rancio (p. ej. un éxito previo) no debe atribuirse al fallo
        // actual. Solo formularios Rumbo dentro de un modal abierto.
        const dialog = form.classList && form.classList.contains('rumbo-form')
            && form.closest ? form.closest('dialog') : null;
        if (dialog && dialog.open) {
            const local = dialog.querySelector('#rumbo-respuesta-notice');
            if (local) local.innerHTML = '';
            const globalBox = document.getElementById('notice-container');
            if (globalBox) globalBox.innerHTML = '';
        }
        const btn = form.querySelector('button[type="submit"]');
        if (!btn || btn.disabled) return;
        btn.dataset.label = btn.textContent;
        btn.textContent = 'Guardando…';
        btn.disabled = true;
    });
    document.body.addEventListener('htmx:afterRequest', function (e) {
        const elt = e.detail && e.detail.elt;
        if (!elt) return;
        const form = elt.closest('#session-form, #nutrition-form, .rumbo-form');
        if (!form) return;
        const btn = form.querySelector('button[type="submit"]');
        if (!btn) return;
        if (btn.dataset.label) {
            btn.textContent = btn.dataset.label;
            delete btn.dataset.label;
        }
        if (form.classList && form.classList.contains('rumbo-form')) {
            btn.disabled = false;
            return;
        }
        const editable = form.id === 'session-form'
            ? editorEditmode() === '1'
            : document.getElementById('nutrition-panel')?.dataset.editmode === '1';
        btn.disabled = !editable;
    });

    // R1+R2: previo de campos para el Ctrl+Z local (foco registra, input/change guardan).
    document.addEventListener('focusin', function (e) {
        const form = e.target.closest && e.target.closest('#session-form, #nutrition-form');
        if (form) noteFormFocus(form);
    });
    document.addEventListener('input', function (e) {
        const field = e.target.closest && e.target.closest('#session-form input, #nutrition-form input');
        if (field) noteFieldEdit(field);
        if (e.target.closest('#session-form')) {
            updateEditActions();
            syncTemplateEjercicios();
            recalcRM();
        }
    });
    document.addEventListener('change', function (e) {
        const sel = e.target.closest && e.target.closest('#session-form select, #nutrition-form select');
        if (sel) noteFieldEdit(sel);
        if (e.target.closest('#session-form')) {
            updateEditActions();
            syncTemplateEjercicios();
            recalcRM();
        }
    });

    document.addEventListener('keydown', function (e) {
        const inField = e.target.closest && e.target.closest('input, textarea');
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
            // R1+R2: fuera de texto solo se restaura el último campo del
            // editor en edición; jamás se llama al undo global del servidor.
            if (e.shiftKey || inField) return;
            if (undoLastFieldEdit()) e.preventDefault();
            return;
        }
        if (e.key === 'Enter' && inField && e.target.closest('#save-template-form input[name="nombre"]')) {
            e.preventDefault();
            confirmEntrenoSave();
        }
    }, true);

    // Protección de cierre/recarga con cambios pendientes: el navegador pide
    // confirmación si algún editor tiene valores sin guardar. isDirty y
    // nutritionIsDirty son defensivas (false sin formulario o tras guardar,
    // porque el swap refresca el baseline); rumboIsDirty cubre día, nombres
    // y respuesta (spec 044 H03) con su propio baseline.
    window.addEventListener('beforeunload', function (e) {
        if (!isDirty() && !nutritionIsDirty() && !rumboIsDirty()) return;
        e.preventDefault();
        e.returnValue = '';
    });
}

function responseUpdatesNutrition(e) {
    const req = e.detail && e.detail.requestConfig;
    const path = (req && req.path) || '';
    if (path.startsWith('/alimentacion') || path.startsWith('/alimento')) return true;
    const xhr = e.detail && e.detail.xhr;
    const txt = xhr && typeof xhr.responseText === 'string' ? xhr.responseText : '';
    if (txt.includes('nutrition-editor-wrap')) return true;
    return false;
}

/* Ctrl+Z local (R1+R2): último campo en edición o nada; lo guardado intacto. */
function undoLastFieldEdit() {
    if (editorEditmode() === '1' && isDirty()) {
        if (popFieldEdit(document.getElementById('session-form'))) return true;
    }
    const panel = document.getElementById('nutrition-panel');
    if (panel && panel.dataset.editmode === '1' && nutritionIsDirty()) {
        if (popFieldEdit(document.getElementById('nutrition-form'))) return true;
    }
    return false;
}
