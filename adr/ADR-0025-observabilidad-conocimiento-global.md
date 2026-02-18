# ADR-0025: Observabilidad y Calidad del Conocimiento Global

- **Estado:** Aceptado
- **Decisores:** Jhonn Muñoz C., AI Assistant (Opencode)
- **Fecha:** 2026-02-16
- **Contexto:** Post-mortem del fallo de ingesta v0.7.2

## Contexto

El reporte `v0.7.2-analisis-fallo-ingesta-global.md` documentó un fallo en el que
el filtro de seguridad de `GlobalKnowledgeLoader._should_process_file()` descartaba
silenciosamente archivos legítimos del sistema (prefijo `CORE_`) que contenían
ISBNs en el nombre, interpretándolos como IDs de usuario de Telegram.

Más allá del bug, el incidente expuso la ausencia de observabilidad en el pipeline
de conocimiento global: fallos silenciosos en ingesta, sin registro de qué está
ingresado, sin trazas RAG, y sin verificación de recuperabilidad.

## Decisión

1. **Lista Blanca CORE_**: Los archivos con prefijo `core_` (case-insensitive) omiten
   la verificación de IDs numéricos. El filtro retorna una tupla `(bool, str)` con
   la razón de aceptación/rechazo para logging explícito.

2. **Auditor de Conocimiento**: Nuevo módulo `knowledge_auditor.py` que consulta la tabla
   `memories` para obtener inventario y estadísticas por documento. Verificación de
   recuperabilidad semántica solo bajo demanda (via endpoint REST).

3. **Trazas RAG en Logs Estructurados**: Cada búsqueda en `VectorMemoryManager.retrieve_context()`
   genera un log JSON enriquecido con: query, fragmentos recuperados, scores, fuentes, y
   latencia. Consultable con `jq` sobre los logs JSON del sistema.

4. **Endpoint de Diagnóstico**: `GET /system/diagnostics/knowledge` retorna el estado completo
   del conocimiento global. Registrado bajo el prefix `/system` existente.

5. **Sin Atribución en Prompt**: Los fragmentos RAG se inyectan como texto plano al LLM,
   sin marcadores de fuente. La trazabilidad se gestiona exclusivamente via logs.

## Consecuencias

### Positivas
- Eliminación de fallos silenciosos en ingesta.
- Visibilidad completa del ciclo de vida del conocimiento (ingesta → almacenamiento → recuperación → uso).
- Capacidad de diagnosticar problemas de calidad RAG sin acceso a la DB.
- Costo cero en almacenamiento adicional (logs, no tablas nuevas).

### Negativas
- El endpoint de diagnóstico con verificación genera N+1 embeddings bajo demanda.
- Volumen de logs incrementado (~200 bytes/búsqueda RAG adicional).
