# PLAN: Herramienta de Ingesta Masiva (Bulk Ingestor)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** Propuesto
- **Fecha:** 2026-02-12
- **Razón de Creación:** Nueva Funcionalidad
- **Objetivo General:** Permitir la importación de historiales de conversación externos (ChatGPT, Claude, WhatsApp) para acelerar la personalización de la memoria de la IA.

---

## Resumen Ejecutivo
Actualmente, AEGEN construye su memoria mensaje a mensaje. Este plan propone la creación de un motor de ingesta masiva que parsee exportaciones históricas y las integre en la memoria de largo plazo con metadatos de procedencia correctos.

---

## Fase 1: Estructura y Parsers Base
### Objetivo
Definir la interfaz de parseo y soportar el formato ChatGPT.

### Justificación
ChatGPT es la fuente más común de historiales previos. Una interfaz abstracta garantiza que podamos añadir nuevos formatos (Claude, WhatsApp) sin rediseñar el motor.

### Cambios Previstos
- **Módulo/Archivo:** `src/tools/bulk_ingestor/`
  - **Acción:** Crear
  - **Descripción:** Directorio para la lógica de importación, incluyendo `base_parser.py` y `chatgpt_parser.py`.

---

## Fase 2: Integración y CLI
### Objetivo
Automatizar la inyección en la base de datos mediante una herramienta de línea de comandos.

### Justificación
Permite al administrador o usuario avanzado cargar datos de forma segura y local.

### Cambios Previstos
- **Módulo/Archivo:** `scripts/bulk_import.py`
  - **Acción:** Crear
  - **Descripción:** Script CLI para ejecutar la ingesta masiva.

---

## Seguimiento de Tareas
- [ ] Definir BaseParser e interfaz de eventos.
- [ ] Implementar parser de JSON de ChatGPT.
- [ ] Implementar parser de WhatsApp (TXT).
- [ ] Integrar con el pipeline de ingesta vectorial.
- [ ] Crear script CLI de importación.

---

## Notas y Riesgos
- **Privacidad:** Los archivos deben procesarse localmente; nunca subirse a nubes externas durante el parseo.
- **Detección de Fechas:** Las exportaciones de WhatsApp varían su formato de fecha según la región, requiriendo un parser flexible.
