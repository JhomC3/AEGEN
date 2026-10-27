# Plan técnico — Spec 048 (H07+H08)

## Estructura de módulos

- H07 (1 regla CSS): eliminar `#daily-page .splits-editor-col` con
  `max-width: 960px` en `static/css/diario.css` (el `min-width: 0` y el flex
  ya existen; la columna pasa a `flex: 1` como Splits/Rumbo).
- H08 (template + CSS con scope): `templates/splits.html` (botón «Nuevo
  split» a cabecera del aside, sticky en escritorio) +
  `static/css/components.css` (misma posición X y altura de
  marca/navegación en las tres pestañas por retirada del botón, sin
  reestructurar el header; reutiliza tokens y botones existentes).
- Tests: `tests/e2e/test_shell_comun_h07_h08.py` (anchos x/w por pestaña a
  1440/390, navX idéntico, alturas de cabecera, botón operable en aside,
  Dashboard intacto vía pines existentes).

## Modelo de datos

Sin cambios. Sin migraciones.

## Algoritmo / contrato

- La navegación conserva la misma posición X en las tres pestañas porque
  la fila de la marca ya no contiene acciones (la marca conserva su
  estructura sin cambios).
- Acciones en el aside (solo Splits): bloque propio sticky en escritorio
  con fondo de página; solo tokens, sin colores ni tipografías nuevas.

## Decisiones técnicas

- No tocar `.dashboard-header` ni el render del Dashboard: scope
  `.splits-page` + pines `test_dashboard_freeze.py` en verde.
- No unificar contenidos distintos: cada pestaña conserva sus controles;
  solo el comportamiento posicional se iguala.

## Estrategia de tests

- Una tarea cada vez: H07 (medición que falla → quitar tope → validar) y
  H08 (medición que falla → botón al aside → validar) + regresión Dashboard.
- Gates §8 en orden.
