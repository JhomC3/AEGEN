# Spec 047 — Legibilidad y operabilidad móvil: contraste y táctil (H10+H11)

Constitución: `docs/constitution.md` (principios 1, 5, 6, 7).
H10 medido vigente (3.78:1 en ayuda 12px, exige ≥4.5:1); H11 con medidas
base (inputs 68×20, acciones 14px visuales, lápiz 24×24) y expansores
declarados sin verificar colisiones. Sin actividad paralela en este alcance
(SENDA es marca no aplicada; `feat/rumbo` es otra área).

## Contexto y objetivo

Corregir legibilidad y operabilidad táctil sin rediseñar la densidad de las
tablas: contraste real AA en ayudas y áreas de interacción verificadas en
móvil, con excepciones por espaciado solo medidas y justificadas.

## Usuarios

Dueño (único usuario local + sync LAN HealthSync).

## Requisitos funcionales (EARS)

- RF-1 (H10): EL SISTEMA mostrará el texto de ayuda `.rumbo-hint` (12 px)
  con el token existente `neutral-400` (7.1–7.9:1 medido sobre fondos
  reales, ≥4.5:1). Solo cambia el texto afectado; la paleta no se modifica.
- RF-2 (H11): En dispositivos sin hover, las acciones de fila serán visibles
  sin depender de hover/foco; en escritorio se conserva hover + foco +
  aparición actual y la densidad de las tablas. Scope explícito: solo
  Diario (`#daily-page`); el popup del Dashboard, congelado, no se altera.
- RF-3 (H11): Cada objetivo táctil cumplirá 24×24 px efectivos (WCAG 2.2 AA)
  o tendrá excepción por espaciado medida y justificada individualmente. Se
  verificará que las áreas ampliadas no se superponen ni activan controles
  vecinos a 320/390/1280 px.
- RF-4 (H11): Medición antes que conservación: inputs, lápiz y expansores
  se mantienen intactos únicamente si cumplen el criterio aprobado; si
  fallan, se corrige lo demostrado sin forzar excepciones para
  conservarlos. Se mantienen los 44 px donde ya existan.

## Requisitos no funcionales

- Solo tokens existentes; sin handlers inline; sin cambios de rutas,
  migraciones ni CSRF; gates §8 en verde.

## Casos límite

| Control | Escritorio | Táctil sin hover |
|---|---|---|
| Acciones de fila (+/−) | hover/foco las muestra | siempre visibles |
| Lápiz edición 24px | intacto | intacto |
| Steppers RIR | hover actual | visibles si hay edición |
| Inputs 20px alto | intactos | intactos + área real verificada |

## Fuera de alcance

- H07/H08 (siguiente lote visual), H12–H14, rediseño de densidad 44px,
  cambios de métricas, navegación y nuevas funcionalidades.

## Criterios de finalización

- Contraste medido ≥4.5:1 en ayudas afectadas; hit-areas ≥24px medidas o
  excepción documentada por control; sin superposiciones a 320/390/1280;
- Sin regresiones en Dashboard (congelado) ni demás pestañas; gates §8.

## Excepción explícita al estándar interno (aprobada 2026-10-04)

El objetivo interno de 44 px no aplica a los controles de tablas compactas
de este lote: rige 24 px WCAG o excepción por espaciado medida y justificada.
Se mantiene 44 px donde ya exista. Sin rediseñar la densidad.

## Excepciones por espaciado (medidas 2026-10-04, editor de sesión a 390 px)

- Lápiz de edición 24×24: cumple directo, sin excepción.
- Píldora +/− y RIR: 24 px efectivos por botón con centros a ≥24 px
  (gaps de 10 px y expansores completos en táctil y escritorio, scope
  Diario; píldora de 24 px exactos con cuneta táctil). Verificado por botón
  exacto en ambos, sin vecino en su área declarada. El borde exterior tras
  el último botón queda fuera del scrollport en el límite de la tabla:
  franja muerta inerte (resuelve fondo, nunca un vecino).
- Inputs de celda (p. ej. 68×20): altura 20 < 24. Excepción: en vertical,
  centros a 24 px y el fallo cae en fondo no interactivo; en horizontal, el
  punto medio entre campos no activa ninguna acción (campo visible o hueco
  inerte). Sin vecino activable por error en ningún eje.

## Geometría R2 (aprobada: RIR en la píldora, fuera de la celda)

Las mitades RIR no caben a 24 px en una fila de 24 px sin solaparse: los
mini-steppers salen de la celda en todas las vistas (CSS, popup intacto) y
RIR vive en la píldora con botones 24×24 sin expansor (▲/▼,
`data-delta` conservado, `aria-label` «Disminuir/Aumentar RIR», distintos
de +/− de fila). Píldora [−][+][▲][▼] con gaps táctiles de 10 px (centros
a ≥24 px, escritorio intacto). La píldora ampliada vive en una cuneta
dedicada táctil (columna de acciones 108/40 px sesión/nutrición) para no
tapar valores; altura 24 px exacta, tangente entre filas. Teclado
(flechas), edición directa, densidad y columnas intactos. Cada variante
vive en un solo DOM por superficie (`placeRirSteppers` en `editor.js`: en
Diario se retiran los de celda con su envoltorio para no interceptar
toques; en el popup, los de la píldora; el CSS oculta cada variante fuera
de su superficie como respaldo sin JS). Verificado: cajas, botón exacto,
contención en cuneta y centros de valores.

## Disenso registrado

Ninguno.
