# Plan técnico — Spec 045 (H04, opción 1)

## Estructura de módulos

- `templates/rumbo.html` (único template tocado): texto honesto del
  `<noscript>` + `<style>` que oculta `.rumbo-actions` (botones de envío de
  día, nombres y respuesta) solo sin JS. Sin clases nuevas, sin Tailwind.
- Tests: `tests/e2e/test_rumbo_sin_js.py` (contexto Playwright con
  `java_script_enabled=False`: aviso, envíos ocultos, lectura preservada) +
  1 test unitario en `tests/test_rumbo_simple_routes.py` (HTML servido: texto
  honesto presente, texto falso ausente).

## Modelo de datos

Sin cambios. Sin migraciones.

## Algoritmo / contrato

El `<style>` dentro de `<noscript>` solo lo aplica el navegador con JS
desactivado; con JS el bloque se ignora y el flujo htmx queda intacto.
Selectores por clase existente (`.rumbo-actions`, `.rumbo-form
button[type="submit"]`): ocultar el contenedor de acciones cubre los tres
formularios sin tocar su markup. Además los botones nacen `disabled` (sin
botón operativo no hay submit implícito por Enter) y JS los habilita al
inicializar y tras cada re-render OOB (salvo vuelo en curso).

## Decisiones técnicas

- Ocultar antes que deshabilitar: sin JS no hay forma de conmutar `disabled`;
  el CSS en `<noscript>` es el mecanismo estándar y la CSP lo permite.
- No se añade `method`/`action`: un POST nativo fallaría por CSRF de
  cabecera y sugeriría un soporte que no existe.
- No se tocan rutas, servicios ni CSRF: cero superficie nueva.

## Estrategia de tests

- Reproducción primero: test no-JS que hoy falla (aviso falso visible).
- Tras el fix: aviso honesto visible, `button[type="submit"]` ocultos en
  `#rumbo-hoy`, `#rumbo-yo` y diálogo (diálogo sin abrir), lectura visible
  (títulos, semana, preguntas), y con JS todo igual (suite existente).
- Gates §8 en orden.
