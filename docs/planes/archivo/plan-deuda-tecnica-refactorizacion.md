# Plan de Refactorización y Eliminación de Deuda Técnica

> **Estado:** Aprobado
> **Fecha:** 17 Feb 2026
> **Versión base:** v0.8.0 (según PROJECT_OVERVIEW.md)
> **Objetivo:** Alcanzar 0 errores en Ruff, 0 errores en Mypy (modo estricto), y cumplimiento al 100% de los límites de arquitectura definidos en AGENTS.md.

---

## 1. Resumen Ejecutivo

La fase de remediación crítica (plan-compliance-remediation.md) eliminó bloqueos de seguridad y errores graves. Quedan **212 errores de Ruff**, **59 errores de Mypy**, **23 funciones sobredimensionadas** y **5 archivos sobredimensionados**.

### Dashboard de Deuda (Línea Base — 17 Feb 2026)

| Herramienta | Errores | Archivos afectados | Regla dominante |
|---|---|---|---|
| Ruff (linter) | 212 | ~55 archivos | E501 = 182 (86%) |
| Mypy (types) | 59 | 31 archivos | no-untyped-def = 34 (58%) |
| Arquitectura (funciones) | 23 funciones >50 líneas | 19 archivos | chat_tool.py = 130 líneas |
| Arquitectura (archivos) | 5 archivos >200 líneas | 5 archivos | session_manager.py = 241 líneas |
| **Total** | **299 violaciones** | | |

### Desglose de Ruff por Regla (212 errores)

| Regla | Cantidad | Descripción | Fix type |
|---|---|---|---|
| E501 | 182 | Línea >88 caracteres | Mecánico |
| PTH123 | 5 | `open()` → `Path.open()` | Mecánico |
| SIM105 | 3 | `try-except-pass` → `contextlib.suppress` | Mecánico |
| S608 | 3 | SQL injection por f-string (falsos positivos con `?` placeholders) | `noqa` |
| UP038 | 2 | `isinstance((X, Y))` → `isinstance(X \| Y)` | Mecánico |
| SIM300 | 2 | Yoda condition detectada | Auto-fix |
| SIM117 | 2 | Nested `with` → single `with` | Mecánico |
| S110 | 2 | `try-except-pass` debe loguear | Semántico |
| S106 | 2 | Falso positivo: `token_type="input"` detectado como password | `noqa` |
| PTH110 | 2 | `os.path.exists()` → `Path.exists()` | Mecánico |
| SIM113 | 1 | Usar `enumerate()` | Mecánico |
| SIM102 | 1 | Nested `if` → single `if` | Mecánico |
| S310 | 1 | URL open audit (ya tiene `noqa` mal ubicado) | `noqa` |
| S112 | 1 | `try-except-continue` debe loguear | Semántico |
| PTH119 | 1 | `os.path` → `pathlib` | Mecánico |
| I001 | 1 | Import sort | Auto-fix |
| C901 | 1 | Complejidad ciclomática >10 | Refactorizar |

### Desglose de Mypy por Regla (59 errores)

| Regla | Cantidad | Fix type |
|---|---|---|
| `no-untyped-def` | 34 | Agregar `-> None` o tipo de retorno |
| `no-any-return` | 19 | Agregar `cast()` o tipar variable intermedia |
| `unused-ignore` | 4 | Eliminar `# type: ignore` obsoletos |
| `redundant-cast` | 1 | Eliminar `cast()` innecesario |
| `assignment` | 1 | Corregir tipo incompatible |

---

## 2. Inventario Completo de Deuda

### 2.A. E501 — Líneas Largas (182 errores en ~50 archivos)

**Top 15 archivos (concentran ~78% de errores E501):**

| # | Archivo | Errores | Causa raíz |
|---|---|---|---|
| 1 | `src/memory/fact_extractor.py` | 17 | Prompt LLM inline |
| 2 | `src/agents/orchestrator/routing/routing_prompts.py` | 17 | Prompt LLM inline |
| 3 | `src/personality/prompt_builder.py` | 11 | Prompt inline + logs |
| 4 | `src/main.py` | 10 | Logs de lifespan largos |
| 5 | `src/memory/evolution_detector.py` | 7 | Prompt LLM inline |
| 6 | `src/agents/orchestrator/graph_routing.py` | 7 | Logs con f-strings |
| 7 | `src/core/schemas/api.py` | 6 | Docstrings de schemas |
| 8 | `src/memory/keyword_search.py` | 5 | Comentarios largos |
| 9 | `src/agents/specialists/cbt/prompt_builder.py` | 5 | Prompt inline |
| 10 | `scripts/migrate_provenance.py` | 5 | SQL + comentarios |
| 11 | `src/memory/services/memory_summarizer.py` | 4 | Prompt inline |
| 12 | `src/core/error_handling.py` | 4 | Logs con f-strings |
| 13 | `src/memory/vector_memory_manager.py` | 3 | Logs |
| 14 | `src/memory/session_processor.py` | 3 | Logs |
| 15 | `src/core/resilience.py` | 3 | Logs con f-strings |
| | **39 archivos restantes** | **~40** | 1-3 errores cada uno |

**Estrategia de resolución E501:**

1. **Prompts LLM inline** (~60 errores): Convertir strings literales largos a concatenación implícita con paréntesis, manteniendo el prompt inline. NO mover a archivos externos (el prompt está acoplado a la lógica).
2. **Logs con f-strings** (~70 errores): Partir el mensaje de log en concatenación implícita `("parte 1 " f"parte 2 {var}")`.
3. **Comentarios y docstrings** (~25 errores): Reformatear a líneas de <=88 caracteres.
4. **SQL y schemas** (~15 errores): Concatenación implícita o `noqa: E501` para queries que pierden legibilidad al partirse.
5. **Scripts** (~12 errores): Mismo tratamiento que logs.

### 2.B. Ruff Non-E501 (30 errores)

**PTH — Pathlib (8 errores):**

| Archivo | Regla | Línea | Fix |
|---|---|---|---|
| `scripts/diagnostic_net.py` | PTH123 | :13 | `open(env_path)` → `Path(env_path).open()` |
| `src/core/prompts/loader.py` | PTH123 | :62 | `open(p, ...)` → `p.open(...)` (ya es Path) |
| `src/memory/backup.py` | PTH123 | (3 instancias) | `open()` → `Path.open()` |
| `src/core/dependencies.py` | PTH110 | :37 | `os.path.exists()` → `Path().exists()` |
| `src/core/dependencies.py` | PTH119 | (1 instancia) | `os.path` → `pathlib` |
| `src/tools/polling.py` | PTH110 | (1 instancia) | `os.path.exists()` → `Path().exists()` |

**SIM — Simplificación (9 errores):**

| Archivo | Regla | Línea | Fix |
|---|---|---|---|
| `src/tools/telegram_interface.py` | SIM105 | :183 | `try/except ImportError: pass` → `contextlib.suppress(ImportError)` |
| `src/tools/telegram/client.py` | SIM105 | (1) | Idem |
| `src/tools/polling.py` | SIM105 | (1) | Idem |
| `src/main.py` | SIM300 | :136, :149 | Yoda conditions: `["*"] == x` → `x == ["*"]` |
| `src/memory/backup.py` | SIM117 | :85, :151 | Nested `with` → `with a, b:` |
| `scripts/simple_check.py` | SIM102 | :31 | Nested `if` → single `if` combinado |
| `scripts/utils/proxy_hunter.py` | SIM113 | :81 | `count += 1` → `enumerate()` |

**S — Seguridad (8 errores, 5 son falsos positivos):**

| Archivo | Regla | Línea | Fix |
|---|---|---|---|
| `scripts/migrate_provenance.py` | S608 | :70 | Falso positivo (usa `?` placeholders) → `noqa: S608` |
| `src/memory/hybrid_search.py` | S608 | :81 | Falso positivo (usa `?` placeholders) → ya tiene `nosec`, agregar `noqa: S608` |
| `src/memory/repositories/memory_repo.py` | S608 | :123 | Falso positivo → ya tiene `nosec`, agregar `noqa: S608` |
| `src/core/observability/prometheus_exporter.py` | S106 | :36, :41 | Falso positivo (`token_type` no es password) → mover `noqa: S106` a la línea correcta (está en la línea siguiente) |
| `src/tools/telegram/client.py` | S110 | (2) | `except: pass` → agregar `logger.debug(...)` |
| `scripts/simple_check.py` | S112 | :27 | `except: continue` → agregar `logger.debug(...)` |

**Otros (3 errores):**

| Archivo | Regla | Fix |
|---|---|---|
| `src/core/dependencies.py:82` | UP038 | `isinstance(x, (A, B))` → `isinstance(x, A \| B)` |
| `scripts/simple_check.py:31` | UP038 | Idem |
| `scripts/simple_check.py:12` | C901 | Complejidad 11>10: extraer lógica de parseo de AST a función `_analyze_file()` |

### 2.C. Mypy — Tipado (59 errores en 31 archivos)

**`no-untyped-def` (34 errores) — Funciones sin tipo de retorno:**

| Archivo | Errores | Funciones afectadas |
|---|---|---|
| `src/memory/knowledge_watcher.py` | 5 | `__init__`, `start`, `stop`, `_watch_loop`, `_process_file` |
| `src/memory/long_term_memory.py` | 3 | `__init__`, `store_episode`, `recall` |
| `src/memory/knowledge_base.py` | 3 | (3 funciones) |
| `src/memory/knowledge_auditor.py` | 3 | (3 funciones) |
| `src/memory/global_knowledge_loader.py` | 3 | `__init__`, `_load_and_index`, `_cleanup` |
| `src/main.py` | 3 | `lifespan`, `log_all_requests` (+1 arg) |
| `src/personality/manager.py` | 2 | (2 funciones) |
| `src/memory/consolidation_worker.py` | 2 | `__init__`, `consolidate_session` |
| `src/memory/backup.py` | 2 | (2 funciones) |
| `src/tools/telegram_interface.py` | 1 | (1 función) |
| `src/tools/polling.py` | 1 | (1 función) |
| `src/tools/image_processing.py` | 1 | (1 función) |
| `src/tools/document_processing.py` | 1 | (1 función) |
| `src/memory/services/memory_summarizer.py` | 1 | `update_memory` (falta type annotation completa) |
| `src/memory/fact_extractor.py` | 1 | (1 función) |
| `src/core/profile_manager.py` | 1 | `__init__` |
| `src/agents/orchestrator/factory.py` | 1 | (1 función, falta annotation completa) |

**`no-any-return` (19 errores) — Retorno de `Any`:**

| Archivo | Errores | Fix |
|---|---|---|
| `src/memory/json_sanitizer.py` | 2 | Agregar `cast()` al retorno |
| `src/memory/fact_extractor.py` | 2 | Tipar variable intermedia |
| `src/memory/evolution_detector.py` | 2 | Tipar variable intermedia |
| `src/agents/orchestrator/routing/routing_decision_builder.py` | 2 | `cast()` al retorno |
| `src/agents/orchestrator/routing/chaining_router.py` | 2 | `cast()` al retorno |
| `src/tools/telegram/client.py` | 1 | `cast()` |
| `src/memory/repositories/profile_repo.py` | 1 | `cast()` |
| `src/memory/repositories/memory_repo.py` | 1 | `cast()` |
| `src/memory/long_term_memory.py` | 1 | `cast()` |
| `src/memory/global_knowledge_loader.py` | 1 | `cast()` |
| `src/api/services/event_processor.py` | 1 | `cast()` |
| `src/api/routers/status.py` | 1 | `cast()` |
| `src/agents/utils/state_utils.py` | 1 | `cast()` |
| `src/agents/orchestrator/routing/event_router.py` | 1 | `cast()` |

**Otros (6 errores):**

| Archivo | Regla | Fix |
|---|---|---|
| `src/core/logging_config.py` | `unused-ignore` (x4) | Eliminar `# type: ignore` obsoletos |
| `src/memory/global_knowledge_loader.py:37` | `assignment` | Tipo de variable incompatible → declarar como `Optional[VectorMemoryManager]` |
| `src/core/observability/llm_wrapper.py` | `redundant-cast` | Eliminar `cast()` innecesario |

### 2.D. Funciones >50 Líneas (23 funciones)

**Tier 1 — Críticas (>65 líneas, requieren refactorización estructural):**

| # | Función | Archivo:Línea | Líneas | Estrategia |
|---|---|---|---|---|
| 1 | `conversational_chat_tool` | `src/agents/specialists/chat/chat_tool.py:27` | 130 | Separar en `_build_context()`, `_invoke_llm()`, `_format_response()` |
| 2 | `cbt_therapeutic_guidance_tool` | `src/agents/specialists/cbt/cbt_tool.py:30` | 120 | Separar en `_validate_input()`, `_build_therapeutic_context()`, `_invoke_cbt()` |
| 3 | `setup_logging` | `src/core/logging_config.py:27` | 112 | Extraer `_configure_handlers()`, `_configure_formatters()`, `_build_config_dict()` |
| 4 | `process_telegram_update` | `src/api/adapters/telegram_adapter.py:16` | 88 | Extraer `_parse_message()`, `_extract_media()`, `_build_event()` |
| 5 | `search` | `src/memory/hybrid_search.py:25` | 86 | Extraer `_merge_scores()`, `_hydrate_results()` |
| 6 | `process_text` | `src/memory/ingestion_pipeline.py:29` | 83 | Extraer `_clean_text()`, `_generate_embeddings()`, `_store_chunks()` |
| 7 | `_consumer` | `src/core/bus/redis.py:79` | 68 | Extraer `_process_message()`, `_handle_error()` |
| 8 | `process_buffered_events` | `src/api/services/debounce_manager.py:56` | 66 | Extraer `_consolidate_fragments()`, `_dispatch_event()` |
| 9 | `build_routing_prompt` | `src/agents/orchestrator/routing/routing_prompts.py:12` | 65 | El prompt es texto literal; resolverlo como parte de E501, no como split de función |
| 10 | `health_check` | `src/api/routers/status.py:98` | 64 | Extraer `_check_redis()`, `_check_sqlite()`, `_check_llm()` |

**Tier 2 — Moderadas (51-65 líneas, refactorización oportunística):**

| # | Función | Archivo:Línea | Líneas |
|---|---|---|---|
| 11 | `search` | `src/memory/keyword_search.py:54` | 62 |
| 12 | `update_memory` | `src/memory/services/memory_summarizer.py:34` | 60 |
| 13 | `extract_context_from_state` | `src/agents/orchestrator/routing/routing_utils.py:112` | 59 |
| 14 | `build` | `src/agents/orchestrator/graph_builder.py:44` | 56 |
| 15 | `route_user_message` | `src/agents/orchestrator/routing/routing_tools.py:15` | 55 |
| 16 | `insert_memory` | `src/memory/repositories/memory_repo.py:23` | 55 |
| 17 | `lifespan` | `src/main.py:40` | 54 |
| 18 | `create_backup` | `src/memory/backup.py:59` | 54 |
| 19 | `consolidate_session` | `src/memory/consolidation_worker.py:44` | 54 |
| 20 | `_apply_chaining_rules` | `src/agents/orchestrator/routing/chaining_router.py:105` | 53 |
| 21 | `search` | `src/memory/vector_search.py:25` | 53 |
| 22 | `save_session` | `src/core/session_manager.py:110` | 51 |
| 23 | `chunk` | `src/memory/chunker.py:88` | 51 |

### 2.E. Archivos >200 Líneas (5 archivos)

| Archivo | Líneas | Exceso | Estrategia |
|---|---|---|---|
| `src/core/session_manager.py` | 241 | +41 | Extraer `SessionConsolidator` → `session_consolidation.py` |
| `src/core/observability/handler.py` | 235 | +35 | Separar `MetricsHandler` → `metrics_handler.py` |
| `src/personality/prompt_builder.py` | 228 | +28 | Mover constantes de template a módulo `prompt_constants.py` |
| `src/core/profile_manager.py` | 220 | +20 | Extraer `ProfileSeeder` → `profile_seeder.py` |
| `src/agents/orchestrator/routing/routing_utils.py` | 206 | +6 | Extraer `IntentParser` → `intent_parser.py` |

---

## 3. Estrategia de Ejecución (4 Fases)

Las fases están ordenadas por **impacto sobre el conteo de errores** (mayor reducción primero) y **riesgo de regresión** (menor riesgo primero).

### Fase 1: Limpieza Mecánica de Ruff (Bajo riesgo, alto impacto)

**Objetivo:** Eliminar 212 → 0 errores de Ruff.
**Esfuerzo estimado:** 3-4 horas.
**Riesgo de regresión:** Mínimo (cambios de formato, no de lógica).

**Paso 1.1 — Auto-fixes (3 errores, ~2 min):**
```bash
ruff check src/ scripts/ --fix  # Corrige I001, SIM300 automáticamente
```

**Paso 1.2 — E501 en prompts LLM (~60 errores, ~90 min):**
Archivos: `fact_extractor.py`, `routing_prompts.py`, `prompt_builder.py`, `cbt/prompt_builder.py`, `evolution_detector.py`, `memory_summarizer.py`.
Técnica: Concatenación implícita con paréntesis. Ejemplo:
```python
# Antes (E501):
"Eres un extractor de hechos estructurados. Tu tarea es identificar datos atómicos..."

# Después:
(
    "Eres un extractor de hechos estructurados. "
    "Tu tarea es identificar datos atómicos..."
)
```

**Paso 1.3 — E501 en logs (~70 errores, ~60 min):**
Archivos: `main.py`, `graph_routing.py`, `error_handling.py`, `chaining_router.py`, y ~30 archivos con 1-3 errores.
Técnica: Partir f-strings largos en concatenación implícita.

**Paso 1.4 — E501 en schemas y comentarios (~40 errores, ~30 min):**
Archivos: `api.py`, `keyword_search.py`, `migrate_provenance.py`, y archivos misc.
Técnica: Reformatear docstrings, comentarios largos, SQL queries.

**Paso 1.5 — Non-E501 mecánicos (22 errores, ~30 min):**

| Acción | Errores | Detalle |
|---|---|---|
| `open()` → `Path.open()` | 5 PTH123 | `backup.py`(3), `loader.py`, `diagnostic_net.py` |
| `os.path.*` → `pathlib` | 3 PTH110+PTH119 | `dependencies.py`(2), `polling.py` |
| `contextlib.suppress()` | 3 SIM105 | `telegram_interface.py`, `client.py`, `polling.py` |
| Nested `with` → single | 2 SIM117 | `backup.py:85`, `backup.py:151` |
| `isinstance` union | 2 UP038 | `dependencies.py:82`, `simple_check.py:31` |
| `enumerate()` | 1 SIM113 | `proxy_hunter.py:81` |
| Nested `if` merge | 1 SIM102 | `simple_check.py:31` |
| Complejidad C901 | 1 | `simple_check.py` → extraer `_analyze_file()` |

**Paso 1.6 — Noqa justificados (8 errores, ~10 min):**

| Archivo | Regla | Acción |
|---|---|---|
| `prometheus_exporter.py:36,41` | S106 | Mover `noqa: S106` de línea 37/42 a línea 36/41 |
| `migrate_provenance.py:70` | S608 | Agregar `noqa: S608` (usa `?` placeholders, seguro) |
| `hybrid_search.py:81` | S608 | Reemplazar `nosec B608` por `noqa: S608` |
| `memory_repo.py:123` | S608 | Reemplazar `nosec B608` por `noqa: S608` |
| `telegram/client.py` | S110 | Agregar `logger.debug()` en `except` |
| `simple_check.py:27` | S112 | Agregar `logger.debug()` en `except` |

**Validación:** `ruff check src/ scripts/` → **0 errores**.

### Fase 2: Tipado Estricto con Mypy (Bajo riesgo, mecánico)

**Objetivo:** Eliminar 59 → 0 errores de Mypy.
**Esfuerzo estimado:** 2-3 horas.
**Riesgo de regresión:** Mínimo (agregar anotaciones no cambia la lógica en runtime).

**Paso 2.1 — `no-untyped-def` (34 errores, ~90 min):**
La mayoría son funciones `async def __init__` o métodos sin `-> None`. Archivos principales:
- `src/memory/knowledge_watcher.py` (5 funciones)
- `src/memory/long_term_memory.py` (3)
- `src/memory/knowledge_base.py` (3)
- `src/memory/knowledge_auditor.py` (3)
- `src/memory/global_knowledge_loader.py` (3)
- `src/main.py` (3, incluyendo `call_next` arg type)
- `src/personality/manager.py` (2)
- 10 archivos restantes con 1 error cada uno

Fix pattern:
```python
# Antes:
async def __init__(self):
# Después:
def __init__(self) -> None:
```

**Paso 2.2 — `no-any-return` (19 errores, ~45 min):**
Agregar `cast()` importando de `typing`. Archivos con 2 errores: `json_sanitizer.py`, `fact_extractor.py`, `evolution_detector.py`, `routing_decision_builder.py`, `chaining_router.py`. 9 archivos con 1 error cada uno.

Fix pattern:
```python
# Antes:
return result.get("data")  # Returns Any
# Después:
return cast(dict[str, Any], result.get("data"))
```

**Paso 2.3 — Cleanup (6 errores, ~15 min):**
- Eliminar 4 `# type: ignore` obsoletos en `logging_config.py`
- Eliminar 1 `cast()` redundante en `llm_wrapper.py`
- Corregir tipo en `global_knowledge_loader.py:37` → `Optional[VectorMemoryManager]`

**Validación:** `mypy src/` → **Found 0 errors**.

### Fase 3: Modularización de Funciones (Riesgo medio, requiere tests)

**Objetivo:** Reducir las 10 funciones de Tier 1 (>65 líneas) a ≤50 líneas.
**Esfuerzo estimado:** 6-8 horas.
**Riesgo de regresión:** Medio (cambios de estructura, requiere cobertura de tests previa).

**Pre-requisito:** Verificar cobertura de tests de cada archivo con `pytest --cov=<modulo>` antes de refactorizar. Si la cobertura es <50% para un archivo, escribir tests primero.

**Orden de ejecución (por impacto descendente):**

1. **`conversational_chat_tool`** (130→~45 líneas):
   - Extraer `_build_chat_context(state, memories, profile) -> str`
   - Extraer `_invoke_chat_llm(prompt, context) -> str`
   - Extraer `_format_chat_response(raw_response, metadata) -> str`

2. **`cbt_therapeutic_guidance_tool`** (120→~40 líneas):
   - Extraer `_validate_cbt_input(state) -> CbtInput`
   - Extraer `_build_therapeutic_prompt(input, next_actions) -> str`
   - Extraer `_invoke_cbt_llm(prompt) -> str`

3. **`setup_logging`** (112→~30 líneas):
   - Extraer `_build_handler_configs() -> list[dict]`
   - Extraer `_build_formatter_configs() -> dict`
   - Extraer `_build_logging_dict_config() -> dict`

4. **`process_telegram_update`** (88→~35 líneas):
   - Extraer `_parse_telegram_message(update) -> ParsedMessage`
   - Extraer `_extract_media_info(message) -> MediaInfo`
   - Extraer `_build_canonical_event(parsed, media) -> CanonicalEventV1`

5. **`search` en `hybrid_search.py`** (86→~40 líneas):
   - Extraer `_merge_rrf_scores(vector_results, keyword_results) -> list[ScoredResult]`
   - Extraer `_hydrate_results(db, result_ids) -> list[Memory]`

6. **`process_text`** (83→~35 líneas):
   - Extraer `_preprocess_text(raw) -> str`
   - Extraer `_chunk_and_embed(text) -> list[Chunk]`
   - Extraer `_persist_chunks(chunks, metadata) -> int`

7. **`_consumer`** (68→~35 líneas):
   - Extraer `_process_stream_message(msg) -> None`
   - Extraer `_handle_consumer_error(e, msg_id) -> None`

8. **`process_buffered_events`** (66→~35 líneas):
   - Extraer `_consolidate_events(buffer) -> ConsolidatedEvent`
   - Extraer `_dispatch_to_orchestrator(event) -> None`

9. **`build_routing_prompt`** (65 líneas):
   - Este caso es especial: la función es 100% texto literal (prompt template).
   - Fix: resolver como parte de E501 (concatenación). La función en sí puede mantener el tamaño si es puramente declarativa.

10. **`health_check`** (64→~30 líneas):
    - Extraer `_check_dependency(name, check_fn) -> DependencyStatus`
    - Usar un loop sobre una lista de checks en lugar de código secuencial.

**Las 13 funciones de Tier 2** (51-65 líneas) se abordan oportunísticamente durante la Fase 3 si el archivo ya está siendo modificado, o se dejan para un ciclo posterior.

**Validación:** `python scripts/simple_check.py` → **0 funciones >50 líneas en Tier 1**. `make test` → **150/150 tests pasando**.

### Fase 4: División de Archivos (Riesgo medio)

**Objetivo:** Reducir los 5 archivos >200 líneas a ≤200 líneas.
**Esfuerzo estimado:** 4-5 horas.
**Riesgo de regresión:** Medio (cambios de imports en archivos dependientes).

| Archivo original | Nuevo módulo | Qué se extrae |
|---|---|---|
| `session_manager.py` (241) | `session_consolidation.py` | `SessionConsolidator` class + lógica de consolidación |
| `handler.py` (235) | `metrics_handler.py` | `MetricsHandler` class + helpers de métricas |
| `prompt_builder.py` (228) | `prompt_constants.py` | Constantes de template (strings largos) |
| `profile_manager.py` (220) | `profile_seeder.py` | `ProfileSeeder` class + datos de seed |
| `routing_utils.py` (206) | `intent_parser.py` | `IntentParser` class + parsing de intents |

**Procedimiento por archivo:**
1. Identificar el bloque lógico a extraer (clase, grupo de funciones, constantes).
2. Crear el nuevo módulo con los elementos extraídos.
3. En el archivo original, importar y re-exportar (compatibilidad hacia atrás).
4. Buscar imports directos en todo `src/` con `grep` y actualizar si es necesario.
5. Ejecutar `make test` después de cada archivo.

**Validación:** `python scripts/simple_check.py` → **0 archivos >200 líneas**. `make test` → **150/150 tests pasando**.

---

## 4. Criterios de Aceptación Final

| Criterio | Métrica objetivo | Comando de verificación |
|---|---|---|
| Ruff | 0 errores | `ruff check src/ scripts/` |
| Mypy | 0 errores en `src/` | `mypy src/` |
| Complejidad | 0 funciones con C901 >10 | `ruff check --select C901` |
| Funciones | 0 funciones Tier 1 >50 líneas | `python scripts/simple_check.py` |
| Archivos | 0 archivos de lógica >200 líneas | `python scripts/simple_check.py` |
| Tests | ≥150 tests pasando, cobertura ≥60% | `make test` / `make coverage` |
| Gate completo | Todo lo anterior combinado | `make verify` |

---

## 5. Procedimiento de Trabajo

1. Crear branch `refactor/technical-debt` desde `develop`.
2. Ejecutar `make verify` para registrar la línea base.
3. **Fase 1** (Ruff): Un commit por paso (1.1-1.6). PR al finalizar.
4. **Fase 2** (Mypy): Un commit por paso (2.1-2.3). PR al finalizar.
5. **Fase 3** (Funciones): Un commit por función refactorizada. PR al finalizar los 10 Tier 1.
6. **Fase 4** (Archivos): Un commit por archivo dividido. PR al finalizar.
7. Ejecutar `make verify` al final de cada fase.
8. Merge a `develop` tras revisión.

**Regla de rollback:** Si `make test` falla después de un cambio, revertir ese commit específico y diagnosticar antes de continuar.

---

## 6. Dependencias y Riesgos

| Riesgo | Mitigación |
|---|---|
| Romper imports al dividir archivos (Fase 4) | Re-exportar desde el módulo original; buscar imports con `grep` |
| Tests insuficientes para Fase 3 | Verificar cobertura antes de refactorizar; escribir tests si <50% |
| Conflictos de merge con desarrollo paralelo | Branch corto; PRs frecuentes por fase |
| Prompts pierden coherencia al reformatear (Fase 1) | Concatenación implícita preserva el string resultante; verificar con `repr()` |
| Falsos positivos de seguridad recurrentes | Documentar cada `noqa` con comentario explicativo inline |
