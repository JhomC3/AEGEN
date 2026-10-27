# Plan técnico — Spec 046 (H06+H09)

## Estructura de módulos

- H06 (CSS con scope Diario, sin JS): `static/css/session-editor.css`
  (`#daily-page #session-editor/#nutrition-panel .table-scroll`: `height:auto`
  + `min-height` por estado + `max-height: var(--table-h)` conservando las
  cotas 452/516 como máximo, no como fijo). Sin cambios de template (el
  servidor ya sirve el nº de filas; el CSS deriva la altura).
- H09 (template + CSS): `templates/partials/rumbo_anual.html` (rama vacía:
  sin SVG, texto aprobado sin enlace) + comprobación de que no hace falta
  CSS nuevo (la tarjeta colapsa a su contenido).
- Tests: `tests/e2e/test_aire_vertical_h06_h09.py` (alturas por estado a
  320/390/1280, Guardar en viewport, vacío anual compacto con texto
  aprobado, con-datos idéntico, crecimiento esperado exacto y persistencia
  en DB aislada).

## Modelo de datos

Sin cambios. Sin migraciones. `serie_anual_52`/semana intactos; el vacío se
decide en template (`serie sin puntos`) con datos ya servidos.

## Algoritmo / contrato

- Altura sesión: cabecera 20 + 24·n filas hasta el techo 452; nutrición:
  cabecera 84 + 24·n hasta el techo 516. Sin mínimo artificial: con 1 fila
  la tabla mide su contenido exacto. Todo en CSS (`height:auto`,
  `max-height`), cero JS de medición.
- Vacío anual: `{% if serie_sin_puntos %}` → bloque compacto; si no, SVG actual.

## Decisiones técnicas

- No tocar el popup del Dashboard: scope `#daily-page` (mismo patrón que H01).
- No reabrir el debate de cotas máximas: 452/516 se conservan como techo.
- Semana sin cambios: respeta spec 019 (0 neutro).

## Estrategia de tests

- Una tarea cada vez: reproducción (medición que falla) → corrección →
  validación (recarga + `server_db_path`).
- H06: `table-scroll` por estado (vacío/pocas/muchas) a 320/390/1280 +
  Guardar en viewport + estabilidad (alturas invariantes tras
  carga/edición/add-row/guardar).
- H09: vacío (sin SVG, compacto, texto aprobado sin enlace) vs con
  datos (SVG presente, medidas iguales a base).
- Gates §8 en orden; pines del Dashboard congelado en verde.
