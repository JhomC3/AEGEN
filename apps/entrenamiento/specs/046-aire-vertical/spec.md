# Spec 046 — Aire vertical: alturas por estado y vacío anual explícito (H06+H09)

Constitución: `docs/constitution.md` (principios 1, 2, 5, 6, 7).
H06 y H09 medidos vigentes en `dev` (sonda 2026-10-04: tabla sesión 452 px
fijos con 1 fila y Guardar en y≈918 a 390×800; anual 309 px con SVG vacío
de 219 px y «pico 0/30»). H10 queda para el siguiente lote.

## Contexto y objetivo

Corregir el uso del espacio vertical sin rediseño: los editores reservan
altura fija aunque haya una sola fila (Guardar queda bajo el primer viewport
móvil) y la tendencia anual ocupa ~340 px con un gráfico vacío cuando no hay
datos. Se sustituye la reserva fija por adaptación al contenido calculada
en CSS, sin medición JS. El crecimiento al añadir/quitar filas es variación
esperada, no un defecto; el rendimiento real (CLS) no está verificado.

## Usuarios

Dueño (único usuario local + sync LAN HealthSync).

## Requisitos funcionales (EARS)

- RF-1 (H06): CUANDO el Diario muestre un día con pocas filas, EL SISTEMA
  ajustará la altura de la tabla a su contenido exacto desde 1 fila
  (cabecera + filas), conservando como máximo las cotas actuales
  (sesión 452 px, nutrición 516 px) con scroll interno por encima.
  La altura la determina el servidor al renderizar (filas conocidas), sin
  medición JS y sin reserva artificial.
- RF-2 (H06): Con 1 fila a 390×800, las acciones Guardar/Cancelar quedan en
  el primer viewport (sin atravesar zona vacía); en edición siguen siempre
  visibles haya o no cambios. Sin medición JS en ningún estado; el
  crecimiento al añadir/quitar filas es esperado y verificado exacto.
- RF-3 (H09): CUANDO la serie anual no tenga ningún punto registrado,
  EL SISTEMA mostrará un estado vacío explícito y compacto (sin SVG, altura
  automática): «Todavía no hay puntuaciones guardadas este año. Guarda tu
  primer día en Rumbo para ver la tendencia.» Sin enlace (la tendencia se
  alimenta de Rumbo, no del Diario) y sin «pico 0/210» como dato observado.
- RF-4 (H09): Con al menos un punto registrado, la tendencia anual se
  muestra igual que hoy (SVG, pico y semanas intactos).
- RF-5 (transversal): Solo tokens visuales; sin handlers inline; contratos
  htmx/OOB y validaciones intactos. Cambios de editor con scope `#daily-page`
  (el popup del Dashboard está congelado y no se toca).

## Requisitos no funcionales

- Estabilidad visual: la altura por estado se calcula en CSS sin medición
  JS (que causó saltos en el pasado). Verificado en pruebas: alturas finales
  y crecimiento esperado exacto; CLS y todos los estados de carga, no.
- WCAG 2.2 AA: el vacío comunica por texto, no solo por ausencia de gráfico;
  foco y nombres accesibles preservados.

## Casos límite

| Estado | Móvil 320/390 | Escritorio 1280+ |
|---|---|---|
| Editor vacío (1 fila) | tabla compacta, Guardar visible | idem, misma regla |
| Editor con pocas filas | altura = contenido exacto | idem |
| Editor con muchas filas | cota actual + scroll interno | idem |
| Anual sin registros | tarjeta compacta + texto aprobado (sin enlace) | idem |
| Anual con registros | gráfico actual | idem |
| Semana todo a 0 | sin cambios (contrato 019: 0 neutro) | idem |
| Añadir/eliminar fila | crece/encoge hasta la cota de forma esperada | idem |

## Fuera de alcance

- H07/H08 (anchos y cabecera), H10 (contraste, siguiente lote), H11
  (verificar áreas táctiles), H12–H14, métricas, navegación, rediseño visual.
- Lectura de respuestas del diálogo sin JS (spec 045) y popup del Dashboard.

## Criterios de finalización

- 1 fila a 390 px: Guardar con `y < 800`; tabla sin zona muerta; recarga y
  guardado persistente verificados en DB aislada.
- Anual vacío: sin SVG, altura compacta, texto aprobado sin enlace; con datos: idéntico.
- Alturas finales y crecimiento esperado verificados en pruebas; CLS y
  rendimiento real, no verificados.
- Sin regresiones en Dashboard (congelado) ni demás pestañas; gates §8.

## Decisiones pendientes de confirmación

- D-1 (producto, resuelta 2026-10-04): texto exacto «Todavía no hay
  puntuaciones guardadas este año. Guarda tu primer día en Rumbo para ver la
  tendencia.», sin enlace (la tendencia se alimenta de Rumbo).
- D-2 (producto, resuelta 2026-10-04): altura exacta desde 1 fila, sin
  reserva artificial; con muchos registros, cota + scroll interno.
- D-3 (producto): alcance editores solo Diario, popup intacto (contrato
  Dashboard congelado; se confirma por revisión de este diff).

## Disenso registrado

Ninguno.
