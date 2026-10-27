# Plan técnico — Spec 047 (H10+H11)

## Estructura de módulos

- H10 (1 línea CSS): `static/css/rumbo.css` (`.rumbo-hint`:
  `neutral-500` → `neutral-400`). Sin tocar plantillas.
- H11 (CSS con scope Diario `#daily-page` + medición): `static/css/session-editor.css`
  (visibilidad de `.row-actions` sin hover vía `@media (hover: none)`,
  conservando `:hover`/`:focus-within` en escritorio; mismos patrones para
  `#nutrition-panel`; steppers RIR igual si la medición lo exige). Sin cambiar
  tamaños visuales salvo fallo medido; el popup del Dashboard no se toca.
- Tests: `tests/e2e/test_movil_legible_h10_h11.py` (contraste calculado
  ≥4.5, hit-areas ≥24 con `elementsFromPoint`/expansores, no-solape a
  320/390/1280, visibilidad sin hover emulado, Dashboard intacto).

## Modelo de datos

Sin cambios. Sin migraciones.

## Algoritmo / contrato

- Contraste: token existente más próximo que cumple, aplicado a la clase
  afectada (todos sus usos viven sobre paneles oscuros).
- Sin-hover: `@media (hover: none) { opacity: 1 }` sobre las píldoras de
  acciones (y steppers RIR si la medición lo exige); el resto del contrato
  visual (posición sticky-right, píldora, ocultas en readonly) intacto.
- Excepciones por espaciado: solo con medida (área, distancia al vecino) y
  justificación individual en la spec.

## Decisiones técnicas

- No se unifican tamaños a 44 px: lo prohíbe el alcance (excepción aprobada).
- No se tocan `components.css` globales salvo necesidad demostrada.
- La verificación de solape usa puntos de muestreo sobre áreas expandidas
  (pseudo-elementos incluidos por medición de `::before` donde aplique).

## Estrategia de tests

- Una tarea cada vez: H10 (repro 3.78 → fix → ≥4.5 medido), luego H11
  (medir áreas reales + solapes → fijar visibilidad/excepciones → validar).
- Gates §8 en orden; pines del Dashboard en verde.
