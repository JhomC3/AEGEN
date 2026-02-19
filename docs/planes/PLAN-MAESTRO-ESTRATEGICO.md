# PLAN: Estratégico Maestro de Implementación (AEGEN)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** En Ejecución
- **Fecha:** 2026-02-12
- **Razón de Creación:** Planificación a largo plazo para la evolución del sistema AEGEN hacia la autonomía total.
- **Objetivo General:** Transformar AEGEN en un sistema de IA autónomo, profesional, con memoria persistente y capacidades de acción externa.

---

## Resumen Ejecutivo
Este plan maestro define la hoja de ruta técnica para AEGEN. Se divide en tres bloques fundamentales: Saneamiento (Bloque A), Expansión de Memoria (Bloque B) y Capacidad de Acción (Bloque C). Actualmente, el sistema ha completado el saneamiento estructural y se prepara para la fase de expansión masiva de contexto.

---

## Bloque A: Saneamiento y Autonomía
### Objetivo
Limpieza total de deuda técnica y automatización de la gestión de conocimientos.

### Justificación
La base legacy de Google Cloud y la dispersión de datos impedían el escalado y la privacidad "local-first" deseada.

### Tareas y Estado
- [x] **A.1 Saneamiento de Raíz**: Unificación de almacenamiento en `/storage` y eliminación de scripts legacy. (Finalizado ✅ 2026-02-11)
- [x] **A.2 Vigilante de Conocimiento**: Sincronización automática de archivos en `storage/knowledge/`. (Finalizado ✅ 2026-02-13)
- [x] **A.3 Overhaul de Personalidad**: Implementación de arquitectura Soul Stack v2 y Espejo Natural. (Finalizado ✅ 2026-02-15)

---

## Bloque B: Expansión de Memoria y Contexto
### Objetivo
Convertir historiales externos en conocimiento estructurado.

### Justificación
La IA es más potente cuanta más información histórica posee del usuario para personalizar su estilo y recomendaciones.

### Tareas y Estado
- [ ] **B.1 Herramienta de Ingesta Masiva (Bulk Ingestor)**: Parsers para exportaciones de WhatsApp, Claude y ChatGPT. (Pendiente ⏳)
- [ ] **B.2 Agente de Revisión de Vida (Life Review)**: Análisis masivo para extraer hitos y valores del perfil. (Pendiente ⏳)
- [ ] **B.3 Olvido Inteligente (Smart Decay)**: Algoritmo de Ranking con factor temporal. (Pendiente ⏳)

---

## Bloque C: Ecosistema de Acción
### Objetivo
Dotar al asistente de capacidad real de acción mediante herramientas.

### Justificación
AEGEN debe pasar de ser un observador a ser un agente proactivo capaz de gestionar agenda y buscar información real.

### Tareas y Estado
- [ ] **C.1 Fábrica de Habilidades**: Infraestructura de registro automático de herramientas. (Pendiente ⏳)
- [ ] **C.2 Integración de Herramientas**: Google Calendar, Búsqueda Web, Análisis de Archivos. (Pendiente ⏳)
- [ ] **C.3 Verificador de Verdad**: Proceso de auto-crítica contra la Bóveda de Conocimiento. (Pendiente ⏳)

---

## Notas y Riesgos
- La transición a memoria local-first requiere una gestión cuidadosa de las migraciones de SQLite.
- Los parsers externos (WhatsApp) son sensibles a cambios de formato de la plataforma.
