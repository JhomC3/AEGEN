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
- [ ] **A.4 Refactor del Sistema de Intents (Prioridad Máxima)**:
  - **Problema:** El `IntentType` enum (`src/core/routing_models.py`) define 10 intents. El `context_retriever.py` hardcodea 3 intents analíticos (`life_review`, `pattern_analysis`, `cross_domain_query`) para activar Graph-RAG. **Ninguno de esos 3 existe en el enum.** El Graph-RAG por intents analíticos es código muerto. Adicionalmente, `routing_tools.py` no incluye `psicotrading` en su Literal.
  - **Solución:** Eliminar la dependencia de intents para el Graph-RAG. Reemplazar por detección data-driven: si los fragmentos recuperados tienen aristas en `memory_edges`, expandir el grafo.
  - (Pendiente ⏳)
- [ ] **A.5 Migrar Facts Legacy a Atómicos en Producción (Prioridad Máxima)**:
  - **Problema:** 439 facts del usuario `6095416210` están en formato JSON blob (pre-ADR-0032). El RAG no puede encontrarlos semánticamente.
  - **Solución:** Ejecutar `make migrate-facts` en la VM de GCP para re-ingestar cada hecho como registro atómico individual con su propio embedding.
  - (En Ejecución 🔄)
- [ ] **A.6 Re-ingestar PDFs Globales con SemanticChunker (Prioridad Máxima)**:
  - **Problema:** Los PDFs en `storage/knowledge/` (TCC, DSM-5) fueron ingeridos con el chunker recursivo plano (400 tok). No tienen estructura jerárquica (Nivel 3 → Nivel 4) ni purificación de ruido.
  - **Solución:** Re-procesar los PDFs usando `use_semantic_chunker=True` en el `IngestionPipeline`. Esto generará chunks padres (Nivel 3) e hijos (Nivel 4) vinculados por `parent_id`, con contenido purificado de ruido.
  - **Verificación:** Los chunks existentes se marcan `is_active=0`. Los nuevos chunks reemplazan a los viejos. El RAG debe encontrar fragmentos semánticamente coherentes en lugar de texto partido a la mitad.
  - (Pendiente ⏳)
- [ ] **A.7 Activar Respaldo en GCS (Prioridad Máxima)**:
  - **Problema:** `GCS_BACKUP_BUCKET = None`. El `CloudBackupManager` es funcional pero nunca se activó. Si la VM se destruye, se pierden todos los datos.
  - **Solución:** 
    1. Crear bucket GCS (ej. `aegen-backups`) con retention policy de 30 días
    2. Configurar `GCS_BACKUP_BUCKET` y `GCS_CREDENTIALS_JSON` en el `.env` de la VM
    3. Verificar en logs que el backup se ejecuta tras cada consolidación
  - (Pendiente ⏳)
- [ ] **A.8 Snapshots Periódicos del Disco de la VM (Prioridad Alta)**:
  - **Problema:** Sin respaldo cloud, el disco de la VM es el único almacén. Un fallo del disco o un delete accidental de la VM destruye todo.
  - **Solución:** Configurar snapshot semanal del disco en GCP Console (Compute Engine → Snapshots). Retención de 4 semanas.
  - (Pendiente ⏳)

---

## Bloque B: Expansión de Memoria y Contexto
### Objetivo
Convertir historiales externos en conocimiento estructurado.

### Justificación
La IA es más potente cuanta más información histórica posee del usuario para personalizar su estilo y recomendaciones.

### Tareas y Estado
- [ ] **B.1 Herramienta de Ingesta Masiva (Bulk Ingestor)**: Parsers para exportaciones de WhatsApp, Claude y ChatGPT. (Pendiente ⏳)
- [ ] **B.2 Agente de Revisión de Vida (Life Review)**: Análisis masivo para extraer hitos y valores del perfil. (Pendiente ⏳)
- [x] **B.3 Olvido Inteligente (Smart Decay)**: Algoritmo de Ranking con factor temporal. (Finalizado ✅ 2026-05-26 — ADR-0030, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Fase 1 Tarea 1.3)
- [x] **B.4 Arquitectura de Memoria Asociativa Multiresolución (Graph-RAG)**: Grafo relacional entre dominios, ingesta atómica de facts, RAG adaptativo y Two-Stage Retrieval. (Finalizado ✅ 2026-05-27 — ADRs 0029-0033, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Todas las fases completadas)
- [ ] **B.5 Aprendizaje de Aristas por Feedback**: Refuerzo y refinamiento de `memory_edges` basado en feedback implícito y explícito del usuario. El `ConsolidationWorker` ajusta pesos y crea/elimina aristas según la retroalimentación conversacional. (Pendiente ⏳)

---

## Bloque C: Ecosistema de Acción
### Objetivo
Dotar al asistente de capacidad real de acción mediante herramientas.

### Justificación
AEGEN debe pasar de ser un observador a ser un agente proactivo capaz de gestionar agenda y buscar información real.

### Tareas y Estado
- [x] **C.1 Fábrica de Habilidades**: Infraestructura de registro automático de herramientas y skills dinámicos. (Finalizado ✅ 2026-05-12)
- [ ] **C.2 Integración de Herramientas**: Google Calendar, Búsqueda Web, Análisis de Archivos. (En Curso 🔄)
- [ ] **C.3 Verificador de Verdad**: Proceso de auto-crítica contra la Bóveda de Conocimiento. (Pendiente ⏳)
- [ ] **C.4 Graph-RAG Universal Data-Driven (Prioridad Máxima)**: La expansión de grafo debe activarse cuando existan datos relevantes, no cuando un intent analítico (que no existe) lo indique.
  - **Bug raíz (ver A.4):** Los intents analíticos hardcodeados en `context_retriever.py` no existen en `IntentType`. El Graph-RAG es código muerto.
  - **Solución:** Reemplazar la lógica de intents analíticos por un chequeo rápido de existencia de aristas: `SELECT 1 FROM memory_edges WHERE origen_id IN (...) LIMIT 1`. Esto cuesta <5ms si no hay aristas, ~50-150ms si las hay. El costo marginal es trivial comparado con el tiempo de respuesta total (~7s).
  - **Verificación:** Una consulta cross-dominio (ej. "¿cómo afecta mi entrenamiento a mi estado de ánimo?") debe retornar fragmentos de al menos 2 dominios distintos conectados por `memory_edges`.
  - **Dependencia:** Requiere que `memory_edges` tenga datos (se genera en cada consolidación, ~10 mensajes). Si no hay aristas, la expansión no se ejecuta y no hay penalización de latencia.
  - (Pendiente ⏳ — Ver plan detallado en `docs/planes/2026-MM-DD-graph-rag-universal.md`)

---

## Notas y Riesgos
- La transición a memoria local-first requiere una gestión cuidadosa de las migraciones de SQLite.
- Los parsers externos (WhatsApp) son sensibles a cambios de formato de la plataforma.
