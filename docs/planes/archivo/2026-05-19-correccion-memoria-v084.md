# PLAN: Corrección de Subsistema de Memoria v0.8.4

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Completado
- **Fecha:** 2026-05-19
- **Razón de Creación:** Corrección de Error
- **ADR Relacionado:** N/A -- No se modifican interfaces (`src/core/interfaces/`), schemas (`src/core/schemas/`), contratos del bus de eventos ni el pipeline de routing. Los cambios son internos al subsistema de memoria.
- **Objetivo General:** Restaurar el pipeline completo de memoria a largo plazo (consolidación, ingesta vectorial y extracción de hechos) para que MAGI pueda aprender y recordar entre sesiones.

---

## Resumen Ejecutivo

Tres errores independientes en el subsistema de memoria impiden que MAGI persista conocimiento de largo plazo. Aunque el bot responde correctamente a mensajes, tiene **amnesia total**: no consolida resúmenes, no almacena vectores semánticos y no extrae hechos de conversaciones largas.

El origen de cada error es distinto: una regresión de interfaz (Incidente #1), un typo de nombre de tabla + omisión de mapeo (Incidente #2), y un modelo LLM con ventana de tokens insuficiente (Incidente #3). Si no se corrige, cada conversación es independiente y el RAG semántico operará con datos vacíos indefinidamente.

**Referencia:** `docs/reportes/v0.8.4-analisis-errores-post-despliegue.md`

---

## Análisis de Impacto

### Dependencias afectadas

Los 3 archivos modificados son internos al subsistema `src/memory/`. No exportan interfaces públicas consumidas por otros módulos:

- `src/memory/consolidation_worker.py` -- Consumido solo por `src/memory/long_term_memory.py:73` (import diferido).
- `src/memory/repositories/memory_repo.py` -- Consumido solo por `src/memory/sqlite_store.py:19` (composición interna).
- `src/memory/fact_extractor.py` -- Consumido por `consolidation_worker.py:39` y `src/memory/services/incremental_extractor.py` (imports diferidos).

No se modifican schemas Pydantic, interfaces abstractas, ni el pipeline de mensajería.

### Cobertura de tests existente

| Componente | Tests existentes | Cobertura del bug |
|---|---|---|
| `consolidation_worker.consolidate_session` | `tests/integration/test_conversational_flow.py:70` (integración) | No cubre el KeyError (requiere Redis live) |
| `memory_repo.insert_vector` | `tests/unit/memory/test_sqlite_store.py:103` (`test_vector_cleanup_trigger`) | **El test usa el nombre correcto** (`memory_vectors`) pero llama via `store.insert_vector()`, que delega al repo con el nombre incorrecto. El test pasa porque la fixture `temp_db` no está definida correctamente (fixture rota). |
| `fact_extractor.extract_facts` | `tests/unit/memory/test_fact_extractor.py` | Solo cubre `_extract_json` y merge. El método público `extract_facts` no tiene test positivo. |

### Verificación del pipeline

- El cambio **no** toca `src/api/`, `src/agents/`, ni `src/tools/telegram/`.
- El flujo Telegram → Webhook → Evento → Router → Especialista → Respuesta **no se ve afectado**.
- Solo se modifica el post-procesamiento en segundo plano (consolidación, ingesta, extracción de hechos).

---

## Fase 1: Corregir Consolidación de Memoria (Incidente #1)

### Objetivo
Restaurar `consolidate_session()` para que obtenga el buffer de mensajes directamente desde `RedisMessageBuffer`, eliminando la dependencia rota de `get_summary()["buffer"]`. Proteger la invocación con manejo de errores en tareas de segundo plano.

### Justificación
Sin esta corrección, cada intento de consolidación falla con `KeyError: 'buffer'` y se traga silenciosamente. MAGI no genera resúmenes de largo plazo ni actualiza el perfil evolutivo del usuario.

### Cambios Previstos

- **Módulo/Archivo:** `src/memory/consolidation_worker.py`
  - **Acción:** Modificar
  - **Descripción:** Reescribir `consolidate_session()` para obtener el buffer directamente via `long_term_memory.get_buffer()` + `buffer.get_messages(chat_id)` en vez de `get_summary()["buffer"]`. El segundo acceso a `get_summary()` (línea 59) para obtener el resumen actualizado se mantiene intacto (ese sí funciona correctamente).
  - **Consumidores:** `src/memory/long_term_memory.py:78`

- **Módulo/Archivo:** `src/memory/long_term_memory.py`
  - **Acción:** Modificar
  - **Descripción:** Envolver la llamada `asyncio.create_task(consolidation_manager.consolidate_session(chat_id))` en línea 78 con un done callback que logee excepciones no capturadas. Aplicar el mismo patrón a `asyncio.create_task(incremental_fact_extraction(...))` en línea 71.
  - **Consumidores:** `src/api/services/event_processor.py:119` (via `store_raw_message`)

- **Módulo/Archivo:** `tests/unit/memory/test_consolidation_worker.py`
  - **Acción:** Crear
  - **Descripción:** Test unitario aislado (sin Redis real) que verifica: (1) `consolidate_session` obtiene mensajes del buffer correctamente, (2) invoca `update_memory`, `extract_facts`, `save_knowledge`, y `log_session_to_memory` en orden, (3) maneja un buffer vacío sin error.
  - **Consumidores:** N/A (test)

### Verificación de Fase

```bash
make verify
pytest tests/unit/memory/test_consolidation_worker.py -v
```

Checklist de alineación arquitectónica:
- [x] Usa inyección de dependencias (obtiene buffer via `long_term_memory.get_buffer()`)
- [x] Maneja errores con degradación suave (try/except existente + nuevo done callback)
- [x] No crea imports eager nuevos (los imports diferidos se mantienen)
- [x] No modifica schemas

---

## Fase 2: Corregir Ingesta Vectorial (Incidente #3)

### Objetivo
Corregir el nombre de tabla `vec_memories` → `memory_vectors` y añadir la inserción en `vector_memory_map` para que los vectores queden vinculados a sus memorias y la búsqueda semántica pueda encontrarlos.

### Justificación
Sin esta corrección, `IngestionPipeline.process_text()` falla en cada chunk con `no such table: vec_memories`. Incluso corrigiendo solo el nombre, sin el INSERT en `vector_memory_map`, `VectorSearch.search()` no puede encontrar los vectores porque hace JOIN contra esa tabla de mapeo.

### Cambios Previstos

- **Módulo/Archivo:** `src/memory/repositories/memory_repo.py`
  - **Acción:** Modificar
  - **Descripción:**
    1. En `insert_vector()` (línea 96): cambiar `vec_memories` por `memory_vectors`.
    2. Añadir un segundo INSERT a `vector_memory_map` inmediatamente después de la inserción del vector, vinculando `vector_id=mid` con `memory_id=mid`.
  - **Consumidores:** `src/memory/sqlite_store.py:126` (delegación)

- **Módulo/Archivo:** `tests/unit/memory/test_sqlite_store.py`
  - **Acción:** Modificar
  - **Descripción:** Corregir la fixture `store` (líneas 10-36) que actualmente está rota (dos `yield` statements, y el nombre `temp_db` usado por los tests no coincide con el nombre `store` de la fixture). Renombrar a `temp_db` y eliminar el bloque duplicado. Verificar que `test_vector_cleanup_trigger` sigue pasando (este test ya valida la cadena completa `memory_vectors` → `vector_memory_map` → cascade delete).
  - **Consumidores:** Todos los tests de este archivo

### Verificación de Fase

```bash
make verify
pytest tests/unit/memory/test_sqlite_store.py -v
```

Checklist de alineación arquitectónica:
- [x] Usa inyección de dependencias (recibe `store` via constructor)
- [x] Maneja errores con degradación suave (try/except + rollback existente)
- [x] No crea imports nuevos
- [x] No modifica schemas (la tabla `vector_memory_map` ya existe en `schema.sql`)

---

## Fase 3: Corregir Extracción de Hechos (Incidente #2)

### Objetivo
Desviar el `FactExtractor` para que use `get_rag_llm()` (Gemini, ventana de 1M tokens) en vez de `get_fast_llm()` (Groq, límite de 8K tokens). Eliminar la instanciación duplicada del singleton.

### Justificación
Groq `gpt-oss-120b` tiene un límite de 8,000 TPM en tier gratuito. Las conversaciones + knowledge base actual superan ese límite regularmente (12,203 tokens en el incidente). Gemini `gemini-2.5-flash-lite` tiene ventana de 1M tokens y ya está configurado como `RAG_MODEL` en el proyecto.

### Cambios Previstos

- **Módulo/Archivo:** `src/memory/fact_extractor.py`
  - **Acción:** Modificar
  - **Descripción:**
    1. Cambiar import: `from src.core.engine import llm` → `from src.core.engine import get_rag_llm`.
    2. En `__init__` (línea 21): cambiar `self.llm = llm` → `self.llm = get_rag_llm()`.
    3. Eliminar la instanciación duplicada del singleton (líneas 110-112): dejar solo una declaración `fact_extractor = FactExtractor()`.
  - **Consumidores:** `src/memory/consolidation_worker.py:39`, `src/memory/services/incremental_extractor.py`

- **Módulo/Archivo:** `tests/unit/memory/test_fact_extractor.py`
  - **Acción:** Modificar
  - **Descripción:** El constructor de `FactExtractor()` ahora llama a `get_rag_llm()`. Los tests existentes instancian `FactExtractor()` directamente pero solo prueban `_extract_json()` and `_merge_knowledge()` (métodos que no usan el LLM). Añadir un `monkeypatch` o mock de `get_rag_llm` al inicio del módulo de test para que la importación del módulo no falle en entornos sin API key. Alternativamente, evaluar si el LLM puede inyectarse como parámetro opcional del constructor.
  - **Consumidores:** N/A (test)

### Verificación de Fase

```bash
make verify
pytest tests/unit/memory/test_fact_extractor.py -v
```

Checklist de alineación arquitectónica:
- [x] Usa inyección de dependencias (`get_rag_llm()` -- factory pattern existente)
- [x] Maneja errores con degradación suave (try/except existente retorna `current_knowledge`)
- [x] No crea imports eager que puedan fallar en cascada (Google SDK ya es dependency del proyecto)
- [x] No modifica schemas

---

## Seguimiento de Tareas

- [ ] **Fase 1.1:** Escribir test `tests/unit/memory/test_consolidation_worker.py`
- [ ] **Fase 1.2:** Corregir `consolidate_session()` en `src/memory/consolidation_worker.py`
- [ ] **Fase 1.3:** Añadir done callback a `asyncio.create_task` en `src/memory/long_term_memory.py`
- [ ] **Fase 1.4:** Ejecutar `make verify` -- debe pasar al 100%
- [ ] **Fase 1.5:** Commit: `fix(memory): restore consolidation buffer access and add task error handling`
- [ ] **Fase 2.1:** Corregir fixture `temp_db` en `tests/unit/memory/test_sqlite_store.py`
- [ ] **Fase 2.2:** Corregir `insert_vector()` en `src/memory/repositories/memory_repo.py` (nombre tabla + mapeo)
- [ ] **Fase 2.3:** Ejecutar `make verify` + `pytest tests/unit/memory/test_sqlite_store.py -v`
- [ ] **Fase 2.4:** Commit: `fix(memory): correct vector table name and add vector_memory_map insertion`
- [ ] **Fase 3.1:** Cambiar LLM de `FactExtractor` a `get_rag_llm()` y eliminar singleton duplicado
- [ ] **Fase 3.2:** Ajustar tests de `test_fact_extractor.py` para el nuevo import
- [ ] **Fase 3.3:** Ejecutar `make verify`
- [ ] **Fase 3.4:** Commit: `fix(memory): switch FactExtractor to Gemini RAG model for larger context window`
- [ ] **Fase 3.5:** Actualizar estado del reporte `docs/reportes/v0.8.4-analisis-errores-post-despliegue.md` a "Corregido"

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.
> Si la implementación diverge del plan original, registrar aquí el qué, el por qué, y el impacto.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos

1. **Fixture `temp_db` rota:** La fixture `store` en `test_sqlite_store.py` tiene dos `yield` statements y su nombre no coincide con el parámetro `temp_db` que usan los tests. Es posible que estos tests no se estén ejecutando correctamente en CI. La Fase 2.1 corrige esto antes de modificar el código de producción.

2. **`EvolutionDetector` y `MemorySummarizer` también usan `llm` global (Groq):** Estos componentes se invocan dentro de `consolidate_session()` y podrían experimentar rate limits similares al Incidente #2 con conversaciones largas. Sin embargo, su payload es más pequeño (solo el resumen, no la conversación completa), por lo que el riesgo es bajo. Se recomienda monitorear en el siguiente despliegue.

3. **`session_logger.py` invoca `IngestionPipeline`:** La corrección de `insert_vector` en Fase 2 también corregirá indirectamente los logs de sesión que se persisten via `log_session_to_memory()` → `IngestionPipeline.process_text()` → `store.insert_vector()`.

4. **Dead code (`session_consolidation.py`, `SessionManager.trigger_consolidation`):** No se aborda en este plan por ser limpieza no relacionada con los errores de producción. Se recomienda registrar como tarea de deuda técnica.
