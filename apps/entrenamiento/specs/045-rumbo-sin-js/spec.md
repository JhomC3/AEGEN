# Spec 045 — Rumbo sin JavaScript: requisito declarado y aviso honesto (H04)

Constitución: `docs/constitution.md` (principios 1, 5, 6, 7).
Cierra la decisión pendiente D-1 de la spec 044: el dueño eligió **opción 1 —
JavaScript obligatorio con aviso honesto** (2026-10-03). No hay necesidad
demostrada que justifique soporte de guardado sin JavaScript.

## Contexto y objetivo

H04 auditado: el `<noscript>` de Rumbo afirma «los formularios guardan igual»,
pero es falso — los formularios solo tienen `hx-post` y el envío cae por GET
sin persistir. Además el CSRF viaja únicamente por cabecera `X-CSRF-Token`
(inaccesible a un POST nativo) y el diálogo de preguntas exige JS para abrirse.
Se declara JS requisito para guardar y usar las preguntas, se corrige el aviso
y los controles dejan de aparentar guardar sin JS. Sin ampliar soporte ni
rediseño.

## Usuarios

Dueño (único usuario local + sync LAN HealthSync).

## Requisitos funcionales (EARS)

- RF-1: CUANDO se abra `/rumbo` sin JavaScript, EL SISTEMA mostrará un aviso
  honesto (`Rumbo necesita JavaScript para guardar y usar las preguntas.`) y
  NUNCA afirmará que los formularios guardan igual.
- RF-2: CUANDO no haya JavaScript, EL SISTEMA impedirá efectivamente el envío
  de día, nombres y respuesta: los botones de envío nacen `disabled` en el
  HTML (sin botón de envío operativo no hay submit implícito por Enter) y
  además quedan ocultos por el estilo en `<noscript>`, de modo que ningún
  control ofrezca guardar ni provoque un envío GET con datos. Con JavaScript,
  la inicialización los habilita y el flujo htmx queda intacto.
- RF-3: Sin JavaScript, EL SISTEMA mantendrá legible todo el contenido
  servido por el servidor (puntuaciones, semana, anual, sliders, nombres y
  preguntas del índice). Con JavaScript, el comportamiento actual queda intacto.
- RF-4: Tras el cambio, NINGÚN template afirmará funcionalidad inexistente
  sin JS (coherencia con `web-standards.md` y los avisos de Diario/Splits).

## Requisitos no funcionales

- Sin rutas nuevas, sin migraciones, sin cambios de CSRF; CSP estática
  (`style-src 'unsafe-inline'` ya permite el `<style>` en `<noscript>`).
- Gate `audit_consistency.py` en verde (sin color/tipografía inline ni hex).

## Casos límite

- Con JavaScript, los botones nacen `disabled` y se habilitan al inicializar
  y tras cada re-render OOB (el swap sustituye el botón); el estado
  `Guardando…` y el anti-doble-submit del ciclo común siguen mandando
  durante el vuelo. Sin JavaScript quedan `disabled` de forma permanente.
- Respuestas del diálogo: sin JS el diálogo no se abre; sus respuestas no son
  legibles sin JS hoy y no se añade lectura inline (fuera de alcance).

## Fuera de alcance

- Soporte de guardado sin JavaScript (POST nativo, token en campo, doble
  respuesta htmx/nativa), lectura de respuestas sin diálogo, rediseño visual.

## Criterios de finalización

- Test de navegador con JS desactivado en verde (aviso honesto, envíos
  ocultos, lectura preservada) + test unitario del HTML + gates §8.

## Disenso registrado

Ninguno. Opción 1 confirmada por el dueño contra la alternativa sin-JS.
