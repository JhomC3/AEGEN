# Revisión independiente del lote 044 — actualización tras P1a/P1b/P2

## Actualización del autor 2026-10-03 (aviso rancio corregido)

El hallazgo de la evaluación final (éxito antiguo «Rumbo guardado.» presentado
como respuesta a un 422) está corregido conforme a RF-2 con spec actualizada:
el espejo al aviso interno solo traslada `.notice-error` del fallo actual,
cada intento limpia los avisos previos y sin aviso propio se muestra el
respaldo local. Regresión en
`tests/e2e/test_review_044_validation.py::test_review_stale_success_not_reused_for_empty_response`
(exige mensaje de error, no reutilización del éxito, y reintento válido).
Historial inferior intacto.

**Dictamen: cierre técnico del lote 044 aprobado por el dueño dentro de su
alcance.** Sin bloqueantes funcionales en los casos revisados. Pendientes:
H04, H06–H14 y verificaciones de navegadores, accesibilidad y rendimiento.

## Historial — dictamen que declaraba pendiente el 422 (superado)

**Los tres fallos de la ronda anterior están corregidos en sus reproducciones. Queda un P2 de RF-2 antes del cierre: error 422 sin aviso.**

Ejecución independiente actual: `test_rumbo_pendientes_h03.py`, `test_rumbo_errores_h02.py`, `test_review_044.py` y `test_review_044_r3r4.py`: **29 passed in 63.81s**. Evidencia `.tmp/review/p1p2.txt`. Las tres reproducciones independientes que fallaban ahora pasan. No se repitieron los gates completos; 243 E2E y demás gates son resultados declarados por el autor.

**R8 — P2 — Guardar una respuesta vacía devuelve 422 sin aviso visible.** Abrir pregunta, desplegar formulario, dejar textarea vacío y pulsar Guardar. El servidor devuelve 422 (validación de FastAPI); el diálogo sigue abierto sin alerta. `mirrorNoticeIntoDialog()` solo traslada un aviso existente en el contenedor global; esta respuesta no trae un aviso OOB. Fuente: `static/js/htmx-lifecycle.js:80–88,193–198`. RF-2 comprende errores 4xx, por lo que está dentro del lote.

Prueba independiente `tests/e2e/test_review_044_validation.py::test_review_empty_response_has_visible_feedback`: **1 failed in 3.58s**. Evidencia `.tmp/review/p2-validation.txt` y `.tmp/review/p2-empty-422.png`.

Corrección acotada: si la respuesta fallida no aporta un aviso propio, mostrar un mensaje útil de respaldo en el contenedor del formulario. No trasladar un aviso antiguo de otra petición ni duplicar el aviso de dominio del 400. Añadir cobertura de 422 sin OOB y reintento válido. Completar la validación, actualizar spec/tareas y después consolidar las ramas según la instrucción del dueño, sin abrir otro worktree.

Los apartados siguientes conservan la evaluación anterior como historial; R5/R6/R7 ya no son pendientes en sus reproducciones verificadas.

## Dictamen anterior — historial

**No listo para cierre/integración.** La coordinación de peticiones resuelve las regresiones presentadas de salida prematura y el aviso de 500 aparece dentro del diálogo. Persisten dos problemas de conservación de ediciones posteriores y un error de validación invisible dentro del modal.

Revisión del código no commiteado de `feat/lote-h01-h05`, base `e847f1c`. Ejecución en copia aislada `codex/revision-044`, con DB de prueba del fixture; sin modificar el worktree del autor ni la DB original.

## Validación independiente

- `test_rumbo_pendientes_h03.py`, `test_rumbo_errores_h02.py` y las tres reproducciones originales de `test_review_044.py`: **23 passed in 53.17s**. Salida `.tmp/review/r3r4.txt`.
- Tres casos adicionales independientes: **3 failed in 9.78s**. Salida `.tmp/review/r3r4-edges.txt`; pruebas `tests/e2e/test_review_044_r3r4.py`.
- Peticiones retenidas con `page.route`/`setdefault` y liberadas manualmente. No se usan sleeps dentro del handler de rutas para establecer el orden. Este método mejora la reproducción previa basada en sleeps.
- No se repitieron los gates completos reportados por el autor. Los 240 E2E y el resto de gates siguen siendo resultados aportados por él.

## R5 — P1 — Éxito de nombres descarta una edición posterior y permite salir

Fuente: `static/js/rumbo.js:281–295`, procesamiento del fragmento OOB de nombres.

Reproducción: editar nombre a VERSION ENVIADA y día a 8; elegir Guardar y salir; retener ambas peticiones; cambiar el nombre a VERSION POSTERIOR SIN GUARDAR; liberar el éxito de nombres y después el éxito de día. Se navega al Dashboard. SQLite contiene VERSION ENVIADA, no la edición posterior.

El contador espera correctamente las dos respuestas, pero el fragmento OOB reemplaza los controles y el baseline se captura del DOM resultante. Por tanto la comparación de cambios ya no conserva la edición posterior que existía antes de la respuesta. Contradice RF-3: ediciones durante la espera mantienen la página.

Corrección: registrar por formulario los valores o una revisión al emitir la petición; preservar el borrador posterior ante el swap y confirmar únicamente la versión enviada. Alternativamente, impedir de forma efectiva y explícita la edición durante el guardado y ajustar el contrato antes de implementar. No basta con añadir condiciones a `rumboIsDirty()` tras haber reemplazado los controles.

## R6 — P1 — Éxito de respuesta cierra un diálogo con un borrador posterior

Fuente: `static/js/rumbo.js:285–287`.

Reproducción: abrir pregunta; escribir RESPUESTA ENVIADA; pulsar Guardar reteniendo el POST; cambiar el texto a RESPUESTA POSTERIOR SIN GUARDAR; liberar la respuesta real de éxito. El diálogo se cierra incondicionalmente. El texto posterior deja de participar en la detección de pendientes porque `respuestaForm()` devuelve null para un diálogo cerrado.

Corrección: comprobar la identidad del formulario/pregunta y la versión enviada antes de cerrar. Si existe edición posterior, mantenerla visible y pendiente, conservando el éxito de la versión anterior. Evitar que una respuesta tardía cierre un diálogo perteneciente a otra pregunta.

## R7 — P2 — Error 400 de dominio sigue detrás del modal

Fuente: `static/js/htmx-lifecycle.js:166–174` y `src/routes/ui_rumbo.py:141`.

Reproducción real, sin simular error HTTP: abrir pregunta, escribir tres espacios y guardar. El servidor devuelve 400 con «La respuesta no puede estar vacía.» dirigido a `notice-container`. La región `rumbo-respuesta-notice` permanece vacía. El diálogo sigue abierto y la captura inspeccionada no muestra el aviso de fallo dentro de él.

El nuevo selector de contenedor solo inserta mensajes para 403/5xx/red. Para 400 confía en el aviso OOB del servidor, que todavía apunta al contenedor global. RF-2 exige aviso visible dentro del diálogo también para 4xx.

Corrección: dirigir el mensaje de dominio a la región del diálogo activo, preservando el mensaje útil y el reintento. Cubrir además errores de validación 422 que no traigan un fragmento OOB.

Evidencia: `.tmp/review/r4-domain-error.png` (inspeccionada visualmente). No se deduce un fallo de lector de pantalla a partir de esta captura.

## Siguiente acción

Reabrir T7/T10 y completar la conservación de versiones de borradores ante respuestas tardías, además del canal de errores 4xx del formulario de respuesta. Añadir las tres regresiones, verificar persistencia y que el borrador posterior sigue visible/pendiente; después repetir gates §8. No ampliar a H04 ni H06–H14 y no realizar commits/merge automáticos.

R1/R2 y las regresiones presentadas de R3/R4 están resueltas. H04, H06–H14, Safari/Firefox/dispositivo físico, accesibilidad completa y rendimiento real continúan pendientes como se declaró.
