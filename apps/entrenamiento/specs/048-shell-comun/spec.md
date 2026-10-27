# Spec 048 — Shell común: anchos y cabecera (H07+H08)

Constitución: `docs/constitution.md` (principios 1, 2, 5, 6, 7).
H07 y H08 medidos vigentes en `dev` (sonda 2026-10-04: editor Diario 960 px
frente a 1117 px en Splits/Rumbo a 1440; navX 645/651/577/651 y alturas de
cabecera 43/45/53/45; en móvil navX alineado pero alturas 123/81/129/81).
Sin actividad paralela en este alcance (SENDA es marca no aplicada;
`feat/rumbo` es otra área; undo/tests son backend).

## Contexto y objetivo

Unificar el comportamiento de los elementos equivalentes del shell sin
rediseño: misma anchura de columna editora en Diario/Splits/Rumbo y misma
alineación de marca/navegación con independencia de las acciones de página.
El Dashboard está congelado y no se toca.

## Usuarios

Dueño (único usuario local + sync LAN HealthSync).

## Requisitos funcionales (EARS)

- RF-1 (H07): EL SISTEMA mostrará la columna editora del Diario con la
  misma anchura que Splits y Rumbo (flex-1 del layout, sin tope propio de
  960 px) a ≥1024 px. Las tablas conservan su propio ancho (max-content +
  scroll interno); sin cambios en ≤1023 px (el tope nunca ligaba en móvil).
- RF-2 (H08): La cabecera compartida (`splits-page-header`, Diario/Splits/
  Rumbo) conservará marca a la izquierda y navegación en la misma posición
  X y altura en las tres pestañas; las acciones de página no viven en la
  fila de la marca.
- RF-3 (H08): El botón «Nuevo split» saldrá de la fila de la marca a la
  cabecera del aside del catálogo (D-2 confirmada; fijo con sticky en
  escritorio, en flujo en móvil, operable sin scroll horizontal); la altura
  de cabecera convergerá entre las tres pestañas y la página no crecerá
  (el aside ya desplaza internamente, como «Nuevo ejercicio»).
- RF-4: Los cambios en parciales/CSS compartidos con el Dashboard serán
  aditivos y con scope (páginas `.splits-page` o clases nuevas); el render
  del Dashboard queda byte-idéntico (pines en verde).

## Requisitos no funcionales

- Solo tokens y vocabulario existentes; sin handlers inline; sin rutas
  nuevas ni migraciones; gates §8 en verde.

## Casos límite

| Estado | Escritorio 1440 | Móvil 390 |
|---|---|---|
| Ancho editor Diario/Splits/Rumbo | mismo x y w (±1 px) | mismo x y w |
| navX Diario/Splits/Rumbo | idéntico | idéntico (ya lo es) |
| Altura cabecera 3 pestañas | idéntica | idéntica salvo controles legítimos de página |
| Nuevo split | cabecera del aside, sin desplazar nav | en flujo, sin scroll-X |
| Dashboard | intacto (pines) | intacto |

## Fuera de alcance

- H12–H14 (meta, al final), métricas, navegación entre pestañas, rediseño
  visual, cambios en el header del Dashboard (congelado: su navX/padding
  propios se documentan como excepción si difieren). H10/H11 ya integrados
  en `dev`; no reabrirlos.

## Criterios de finalización

- Medidas H07/H08 igualadas según tabla; «Nuevo split» operable en
  cabecera del aside en móvil y escritorio; persistencia y demás flujos intactos;
  Dashboard byte-idéntico; gates §8.

## Decisiones pendientes de confirmación

- D-1 (producto, resuelta 2026-10-04): ancho completo como Splits/Rumbo;
  quitar el tope 960 sin cambiar móvil ni forzar columnas. Verificar en
  escritorio legibilidad de campos y acciones accesibles.
- D-2 (producto, confirmada 2026-10-05): «Nuevo split» en la cabecera del
  catálogo (aside). Historial: primero se aprobó una barra bajo cabecera,
  pero su implementación rompía el encaje exacto (+19 px, regresión
  demostrada en `test_splits_solo_un_abierto`); se sustituyó por el aside
  verificado (encaje, visibilidad y posición de nav intactos, como
  «Nuevo ejercicio»).
- D-3 (pendiente de confirmación en revisión): residuo del Dashboard
  congelado como excepción documentada si difiere tras el cambio.

## Disenso registrado

Ninguno.
