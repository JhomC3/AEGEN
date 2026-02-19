# Plan de Refactorización Integral v0.7.1: Saneamiento de Código y Deuda Técnica

> **Estado:** Aprobado
> **Objetivo:** Reducir la deuda técnica acumulada, eliminar violaciones de SRP, y asegurar que todos los archivos cumplan con los límites de `RULES.MD` (200 LOC para lógica).
> **Alcance:** 17 archivos críticos, código muerto, duplicación DRY y mejoras en herramientas de calidad.

---

## Resumen Ejecutivo

El análisis del codebase ha revelado **17 archivos** que exceden el límite de 200 líneas de código, incluyendo archivos críticos como `webhooks.py` (403 líneas) y `routing_analyzer.py` (348 líneas). Además, se han detectado **10 clases muertas** en esquemas y **funciones duplicadas** entre especialistas.

Este plan aborda la refactorización en 6 fases priorizadas, comenzando por la limpieza y utilidades compartidas, seguido por los archivos más críticos, y terminando con mejoras en el tooling de calidad.

**Métricas de Éxito:**
- 0 archivos de lógica > 200 LOC.
- 0 métodos > 30-40 LOC (salvo excepciones justificadas).
- Eliminación de código muerto detectado.
- `make verify` pasando exitosamente en cada fase.

---

## Fase 0: Limpieza Previa (Quick Wins)
*Objetivo: Eliminar ruido y código muerto antes de refactorizar.*

### Tarea 0.1: Eliminación de Esquemas Muertos
**Archivos:** `src/core/schemas/` (`api.py`, `agents.py`, `documents.py`, `graph.py`, `common.py`)
- Eliminar las 10 clases marcadas con `# TODO: Evaluar eliminacion`.
- Limpiar sus referencias en `__init__.py`.

### Tarea 0.2: Limpieza de Dependencias No-Op
**Archivos:** `src/core/dependencies.py`, `src/main.py`
- Eliminar función `initialize_global_collections()` (no-op).
- Eliminar su invocación en el startup.

### Tarea 0.3: Corrección de Importaciones
**Archivo:** `src/memory/hybrid_search.py`
- Mover `import json` desde el cuerpo de funciones al nivel superior.

---

## Fase 1: Extracciones Transversales (Shared Utilities)
*Objetivo: Crear utilidades compartidas para eliminar duplicación (DRY).*

### Tarea 1.1: Unificar Formateo de Conocimiento
**Origen:** `cbt_specialist.py`, `chat_agent.py`
**Destino:** `src/agents/utils/knowledge_formatter.py`
- Extraer función `format_knowledge_for_prompt()` que está duplicada.
- Refactorizar ambos agentes para usar la utilidad compartida.

### Tarea 1.2: Herramienta de Historial Compartida
**Origen:** `cbt_specialist.py`
**Destino:** `src/agents/utils/history_tool.py`
- Extraer `query_user_history()` para que sea reutilizable por cualquier agente.

---

## Fase 2: Refactorización Crítica (>300 LOC)
*Objetivo: Descomponer los 4 archivos más grandes del sistema.*

### Tarea 2.1: Desmembrar Webhooks (403 LOC)
**Archivo:** `src/api/routers/webhooks.py`
- **Crear** `src/api/adapters/telegram_adapter.py`: Parsing y validación de Telegram.
- **Crear** `src/api/services/event_processor.py`: Lógica de orquestación de eventos.
- **Crear** `src/api/services/debounce_manager.py`: Lógica de buffer y debounce.
- **Crear** `src/api/services/fragment_consolidator.py`: Utilidad de consolidación.
- **Reducir** `webhooks.py` a solo definición de rutas FastAPI (< 80 LOC).

### Tarea 2.2: Modularizar Routing Analyzer (348 LOC)
**Archivo:** `src/agents/orchestrator/routing/routing_analyzer.py`
- **Crear** `src/agents/orchestrator/routing/routing_decision_builder.py`: Construcción de objetos de decisión.
- **Crear** `src/agents/orchestrator/routing/routing_enhancer.py`: Lógica de enriquecimiento de decisiones.
- **Mover** formateo de contexto a `routing_utils.py`.

### Tarea 2.3: Separar Patrones de Routing (334 LOC)
**Archivo:** `src/agents/orchestrator/routing/routing_patterns.py`
- **Crear** `src/agents/orchestrator/routing/pattern_extractor.py`: Clase `PatternExtractor`.
- **Crear** `src/agents/orchestrator/routing/intent_validator.py`: Clase `IntentValidator`.
- **Crear** `src/agents/orchestrator/routing/intent_patterns_data.py`: Diccionario `INTENT_PATTERNS` (Data file).
- **Crear** `src/agents/orchestrator/routing/specialist_mapper.py`: Clase `SpecialistMapper`.

### Tarea 2.4: Estructurar Especialista CBT (333 LOC)
**Archivo:** `src/agents/specialists/cbt_specialist.py`
- **Crear directorio:** `src/agents/specialists/cbt/`
- **Mover** construcción de prompts a `cbt/prompt_builder.py`.
- **Mover** herramienta principal a `cbt/cbt_tool.py`.
- **Mantener** definición de clase y nodo en `cbt_specialist.py` (o `cbt/agent.py`).

---

## Fase 3: Refactorización Alta (250-300 LOC)
*Objetivo: Normalizar archivos de lógica complejos.*

### Tarea 3.1: Observabilidad LLM (298 LOC)
**Archivo:** `src/core/observability/handler.py`
- Extraer lógica de exportación a Prometheus a `src/core/observability/prometheus_exporter.py`.

### Tarea 3.2: Gestor de Perfiles (283 LOC)
**Archivo:** `src/core/profile_manager.py`
- Extraer lógica de localización a `src/core/profile_localization.py`.
- Extraer extracción de contexto a `src/core/profile_context.py`.
- Extraer evolución a `src/core/profile_evolution.py`.

### Tarea 3.3: Gestor de Sesiones (282 LOC)
**Archivo:** `src/core/session_manager.py`
- Extraer lógica de consolidación a `src/core/session_consolidation.py`.

### Tarea 3.4: Worker de Consolidación (275 LOC)
**Archivo:** `src/memory/consolidation_worker.py`
- Extraer detección de evolución a `src/memory/evolution_detector.py`.
- Extraer aplicación de evolución a `src/memory/evolution_applier.py`.
- Extraer persistencia de logs a `src/memory/session_logger.py`.

### Tarea 3.5: Store SQLite (267 LOC)
**Archivo:** `src/memory/sqlite_store.py`
- Separar repositorio de memorias en `src/memory/repositories/memory_repo.py`.
- Separar repositorio de perfiles en `src/memory/repositories/profile_repo.py`.

### Tarea 3.6: Polling Telegram (263 LOC)
**Archivo:** `src/tools/polling.py`
- Extraer cliente HTTP persistente a `src/tools/telegram/client.py`.
- Extraer lógica de reenvío a `src/tools/telegram/forwarder.py`.

### Tarea 3.7: Chat Specialist (262 LOC)
**Archivo:** `src/agents/specialists/chat_agent.py`
- Crear directorio `src/agents/specialists/chat/`.
- Usar formatter compartido (Fase 1).
- Extraer lógica multimodal a `chat/multimodal.py`.

### Tarea 3.8: Configuración de Logging (256 LOC)
**Archivo:** `src/core/logging_config.py`
- Mover formatters y filtros a `src/core/logging/formatters.py`.
- Mover TypedDicts a `src/core/logging/types.py`.

### Tarea 3.9: Master Orchestrator (254 LOC)
**Archivo:** `src/agents/orchestrator/master_orchestrator.py`
- Extraer funciones de enrutamiento de grafo a `src/agents/orchestrator/graph_routing.py`.

---

## Fase 4: Refactorización Menor (200-250 LOC)
*Objetivo: Pulir archivos que exceden ligeramente el límite.*

### Tarea 4.1: Chunker Recursivo (240 LOC)
**Archivo:** `src/memory/chunker.py`
- Refactorizar método `chunk()` (115 LOC) descomponiéndolo en 4-5 métodos privados (`_process_split`, `_create_chunk`, etc.) dentro de la misma clase.

### Tarea 4.2: Memoria a Largo Plazo (225 LOC)
**Archivo:** `src/memory/long_term_memory.py`
- Extraer generación de resúmenes a `src/memory/services/memory_summarizer.py`.
- Extraer extracción incremental a `src/memory/services/incremental_extractor.py`.

### Tarea 4.3: Cola de Mensajes (225 LOC)
**Archivo:** `src/core/messaging/message_queue.py`
- Extraer dataclass `Message` a `src/core/messaging/types.py`.
- Separar `UserMessageQueue` a `src/core/messaging/user_queue.py`.

### Tarea 4.4: Interfaz Telegram (203 LOC)
**Archivo:** `src/tools/telegram_interface.py`
- Mover wrappers `@tool` a `src/tools/telegram/tools.py`.

---

## Fase 5: Mejora de Herramientas de Calidad
*Objetivo: Evitar regresiones y mejorar la detección automática.*

### Tarea 5.1: Script de Verificación Inteligente
**Archivo:** `scripts/simple_check.py`
- Actualizar lógica para distinguir límites: 200 LOC para lógica, 300 LOC para definiciones/schemas.

### Tarea 5.2: Hardening de Tests
**Archivo:** `pyproject.toml`
- Configurar gate de cobertura: `--fail-under=85`.
- (Opcional) Habilitar reglas estrictas de `mypy`.

### Tarea 5.3: Integración de Seguridad
**Archivo:** `makefile`
- Agregar ejecución de `safety` en el target `lint`.

---

## Fase 6: Auditoría Final

1. Ejecutar `make verify` completo.
2. Generar reporte de líneas de código post-refactorización.
3. Actualizar `PROJECT_OVERVIEW.md` reflejando la nueva estructura.
4. Archivar este plan.
