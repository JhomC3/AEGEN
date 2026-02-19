# PLAN: Observabilidad y Calidad del Conocimiento Global

- **Estado:** Completado
- **Fecha:** 2026-02-16
- **Razón de Creación:** Informe de Errores
- **Objetivo General:** Resolver fallos de ingesta silenciosa y dotar al sistema de trazabilidad completa en el proceso RAG.

---

## Resumen Ejecutivo
Se identificó que archivos críticos de la base de conocimiento eran descartados por un filtro de seguridad defectuoso. Este plan implementó una lista blanca, un auditor de conocimiento y logs enriquecidos para verificar el uso real de la información.

---

## Fase 1: Auditor de Conocimiento
### Objetivo
Crear visibilidad sobre lo que realmente está almacenado en la memoria global.

### Justificación
No se puede confiar en un sistema RAG si no hay herramientas para auditar la presencia y recuperabilidad de los documentos fuente.

### Cambios Previstos
- **Módulo/Archivo:** `src/memory/knowledge_auditor.py`
  - **Acción:** Crear
  - **Descripción:** Motor de inventario y estadísticas de memoria global.

---

## Seguimiento de Tareas
- [x] Corregir filtro de ingesta (CORE_ whitelist). ✅ (2026-02-16)
- [x] Implementar `KnowledgeAuditor`. ✅ (2026-02-16)
- [x] Añadir trazas RAG detalladas en logs JSON. ✅ (2026-02-16)
- [x] Crear endpoint `/system/diagnostics/knowledge`. ✅ (2026-02-16)

---

## Notas y Riesgos
- Se generó el ADR-0025 para formalizar las decisiones de observabilidad tomadas.
