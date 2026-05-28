# PLAN: Arquitectura de Memoria Asociativa Multiresolución (v0.9.0)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Completado
- **Fecha:** 2026-05-26
- **Razón de Creación:** Nueva Funcionalidad + Corrección de Deuda Técnica
- **ADRs Relacionados:**
  - `adr/ADR-0029-migracion-consolidacion-gemini.md` — Migración de modelos de background a Gemini
  - `adr/ADR-0030-time-decay-two-stage-retrieval.md` — Time Decay real en búsqueda híbrida
  - `adr/ADR-0031-rag-graphstate-context-retriever.md` — RAG en GraphStateV2 + nodo dedicado
  - `adr/ADR-0032-ingesta-atomica-facts-embedding-cache.md` — Ingesta atómica + caché de embeddings
  - `adr/ADR-0033-memory-edges-graph-rag.md` — Grafo de relaciones transversales
- **Objetivo General:** Eliminar la inestabilidad de producción (error 413), implementar recuperación de memoria temporalmente coherente, y construir el grafo de relaciones entre dominios que habilita el razonamiento analítico multi-salto de MAGI.
- **Documento de referencia:** `docs/arquitectura/investigacion/2026-05-22-analisis-eficiencia-tokens-memoria.md`

---

## Resumen Ejecutivo

El subsistema de memoria de AEGEN v0.8.4 tiene doce gaps documentados que producen tres síntomas visibles: errores `413` de producción que enmudecen el bot, recuperación de contexto ruidosa que degrada la calidad de respuestas, y crecimiento infinito de la base de datos sin decaimiento temporal.

Este plan implementa la solución completa en tres fases ordenadas por dependencia técnica y ROI. La Fase 1 elimina los fallos de producción sin tocar el schema de la DB. La Fase 2 refactoriza la arquitectura RAG y la ingesta. La Fase 3 materializa el grafo relacional completo. Cada fase es un entregable autónomo y verificable — si la Fase 2 se bloquea, la Fase 1 ya habrá estabilizado producción de forma permanente.

**Impacto de no hacer nada:** El bot continuará silenciándose en conversaciones largas. La calidad de memoria se degradará con el tiempo por acumulación de hechos contradictorios sin decaimiento. La base de datos crecerá indefinidamente.

---

## Análisis de Impacto Global

### Dependencias afectadas por módulo

```
src/memory/hybrid_search.py
  → Consumido por: src/memory/vector_memory_manager.py
  → Consumido por (indirecto): src/personality/skills/chat/tools.py
                                src/personality/skills/tcc/tools.py

src/memory/embeddings.py
  → Consumido por: src/memory/ingestion_pipeline.py
                   src/memory/vector_memory_manager.py (retrieve_context)

src/memory/knowledge_base.py
  → Consumido por: src/memory/consolidation_worker.py
                   src/personality/skills/chat/tools.py
                   src/personality/skills/tcc/tools.py

src/memory/consolidation_worker.py
  → Consumido por: src/memory/long_term_memory.py (import diferido)

src/memory/services/memory_summarizer.py
  → Consumido por: src/memory/consolidation_worker.pyB

src/core/schemas/graph.py (GraphStateV2)
  → Consumido por: src/agents/orchestrator/graph_builder.py
                   src/agents/orchestrator/master_orchestrator.py
                   todos los nodos del grafo LangGraph

src/memory/schema.sql + migration.py
  → Afecta: la DB de producción en storage/
```

### Cobertura de tests existente relevante

| Componente modificado | Tests existentes |
|---|---|
| `hybrid_search.py` | `tests/unit/memory/` — verificar con `grep -r 'HybridSearch\|hybrid_search' tests/` |
| `embeddings.py` | `tests/unit/memory/` — verificar con `grep -r 'EmbeddingService\|embeddings' tests/` |
| `knowledge_base.py` | `tests/unit/memory/` — verificar con `grep -r 'KnowledgeBase\|knowledge_base' tests/` |
| `memory_summarizer.py` | `tests/unit/memory/` — verificar con `grep -r 'MemorySummarizer' tests/` |
| `GraphStateV2` | `tests/unit/core/` y `tests/integration/` — verificar con `grep -r 'GraphStateV2' tests/` |

> **Regla:** Si la cobertura de un componente es cero antes de modificarlo, crear el test mínimo ANTES de cambiar el código.

### Verificación del pipeline de mensajería

Las Fases 1 y 2 no tocan `src/api/`, `src/agents/orchestrator/routing/`, ni `src/tools/telegram/`. La Fase 2 añade un nodo al grafo pero no modifica el enrutador ni el adaptador de Telegram. La Fase 3 modifica `schema.sql` y `migration.py` — requiere verificación de que el lifespan de FastAPI ejecuta migraciones correctamente antes de aceptar tráfico.

---

## Fase 1 — Estabilidad de Producción

**Estado:** Completado
**Objetivo:** Eliminar la causa raíz del error `413`, implementar Time Decay real y limpiar deuda técnica sin cambios de schema. Al final de esta fase, el bot nunca vuelve a silenciarse por Rate Limit de Groq y el ranking de memorias es temporalmente coherente.
**Prerrequisito:** Ninguno. Esta fase no depende de ninguna otra.
**Verificación final de fase:** `make verify` pasa al 100%. Probar una conversación de 15+ mensajes sin error 413. Verificar en logs que `consolidation_worker` usa `get_rag_llm()`.

---

### Tarea 1.1 — Migrar `MemorySummarizer` a Gemini (ADR-0029)

- **Archivo:** `src/memory/services/memory_summarizer.py`
- **Acción:** Modificar
- **Línea de referencia:** `:64` (instancia del modelo global Groq)
- **Descripción técnica:**
  1. Localizar la instancia del `llm` global (Groq) usada para construir la cadena de sumarización.
  2. Reemplazar por `get_rag_llm()` importado desde `src/core/engine.py` (ya devuelve Gemini Flash).
  3. Añadir degradación suave: si `get_rag_llm()` lanza excepción en la instanciación, loggear con `structlog` y retornar resumen vacío en lugar de propagar el error.
- **Consumidores afectados:** `src/memory/consolidation_worker.py` (no requiere cambios — interfaz pública de `MemorySummarizer` es estable).
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "summarizer" -v`

---

### Tarea 1.2 — Migrar `EvolutionDetector` a Gemini (ADR-0029)

- **Archivo:** `src/memory/consolidation_worker.py`
- **Acción:** Modificar
- **Línea de referencia:** `:18` (import/instancia del `llm` global para `EvolutionDetector`)
- **Descripción técnica:**
  1. Localizar dónde `consolidation_worker.py` instancia o importa el `llm` global para `EvolutionDetector`.
  2. Reemplazar por `get_rag_llm()`.
  3. Envolver la llamada a `EvolutionDetector.detect_evolution()` en `try/except` con log estructurado en caso de fallo — la consolidación no debe abortar si la detección de evolución falla.
- **Consumidores afectados:** `src/memory/long_term_memory.py` (no requiere cambios).
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "consolidat" -v` y `pytest tests/integration/ -k "conversational" -v`

---

### Tarea 1.3 — Implementar Time Decay en `HybridSearch` (ADR-0030)

- **Archivo:** `src/memory/hybrid_search.py`
- **Acción:** Modificar (refactorización del método de búsqueda)
- **Descripción técnica:**
  1. En `src/core/config/base.py`, añadir:
     ```python
     MEMORY_DECAY_LAMBDA: float = 0.01   # λ para decaimiento exponencial temporal
     MEMORY_RETRIEVAL_POOL: int = 100     # candidatos en Etapa 1 del Two-Stage
     MEMORY_RETRIEVAL_TOP_K: int = 15     # resultado final tras re-ranking
     ```
  2. En `HybridSearch.search()`:
     - Cambiar el límite de consulta a `vector_search.search(embedding, limit=settings.MEMORY_RETRIEVAL_POOL)` y `keyword_search.search(query, limit=settings.MEMORY_RETRIEVAL_POOL)`.
     - Aplicar RRF sobre los 100 candidatos como antes.
     - Añadir método privado `_apply_time_decay(results: list[dict]) -> list[dict]`:
       ```python
       import math
       from datetime import datetime, timezone

       def _apply_time_decay(self, results: list[dict]) -> list[dict]:
           now = datetime.now(timezone.utc)
           lambda_ = settings.MEMORY_DECAY_LAMBDA
           for r in results:
               created_at = r.get("created_at")
               if created_at is None:
                   continue  # sin penalización: score_final = score_similitud
               delta_days = (now - created_at).total_seconds() / 86400
               r["score"] = r["score"] * math.exp(-lambda_ * delta_days)
           return sorted(results, key=lambda x: x["score"], reverse=True)
       ```
     - Aplicar `_apply_time_decay()` tras el RRF y retornar `[:settings.MEMORY_RETRIEVAL_TOP_K]`.
  3. Asegurar que `created_at` se hidrata correctamente en `_hydrate()` (ya existe en `memories.created_at` — verificar que el SELECT lo incluye).
  4. Añadir manejo de `created_at` como `datetime` (no string): parsear con `datetime.fromisoformat()` si viene como string de SQLite.
- **Consumidores afectados:** `src/memory/vector_memory_manager.py` — los límites hardcoded `limit=2`, `limit=3` en los tools de especialistas ahora son ignorados en favor de `MEMORY_RETRIEVAL_TOP_K` centralizado. Verificar que `retrieve_context()` propague el nuevo pool correctamente.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "hybrid" -v`. Añadir test que verifique que una memoria de 200 días tiene menor `score` que una de 1 día con igual similitud semántica.

---

### Tarea 1.4 — Filtrado por `context_type` en Tools de Especialistas

- **Archivos:** `src/personality/skills/chat/tools.py`, `src/personality/skills/tcc/tools.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. En `_get_chat_rag_context()` y `_get_cbt_rag_context()`, añadir el parámetro `context_type=["fact", "document"]` en la llamada a `manager.retrieve_context()`.
  2. Eliminar la recuperación de `memory_type="conversation"` del pool de RAG semántico — el historial de conversación ya se gestiona por el buffer de historial en ventana, no por el RAG vectorial.
  3. Separar la recuperación de `document_parent` (fuentes externas) de `fact` (hechos del usuario) si `retrieve_context()` lo soporta. Si no lo soporta actualmente, hacerlo en dos llamadas separadas con sus propios límites.
- **Test a ejecutar:** `pytest tests/unit/ -k "rag_context or chat_tool or cbt_tool" -v`

---

### Tarea 1.5 — Activar Embedding Cache (ADR-0032, parte B)

- **Archivos:** `src/memory/embeddings.py`, `src/memory/migration.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. En `migration.py`, añadir en la función de migraciones idempotentes:
     ```sql
     CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash
     ON embedding_cache(content_hash);
     ```
  2. En `EmbeddingService.embed_query()` y `embed_documents()`:
     - Antes de llamar a la API: `SELECT embedding FROM embedding_cache WHERE content_hash = ?` usando el SHA-256 del texto (ya existe `deduplicator.py` con esta lógica — reutilizar `compute_hash()`).
     - Si hit: deserializar el BLOB con `numpy.frombuffer()` o equivalente y retornar.
     - Si miss: llamar a la API, serializar el vector con `.tobytes()`, insertar en `embedding_cache` con `INSERT OR IGNORE`.
     - Todo async con `aiosqlite`.
  3. La conexión a SQLite debe recibirse por inyección de dependencias, no instanciarse internamente.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "embedding" -v`. Añadir test que verifique que la segunda llamada con el mismo texto no llama a la API externa (mockear la API).

---

### Tarea 1.6 — Eliminar `session_processor.py` (Código Muerto)

- **Archivo:** `src/memory/session_processor.py`
- **Acción:** Eliminar
- **Descripción técnica:**
  1. Ejecutar `grep -r 'session_processor\|SessionProcessor' src/ tests/` — confirmar cero referencias activas.
  2. Si hay referencias en tests, eliminarlas también (son tests de código muerto).
  3. Eliminar el archivo.
  4. Ejecutar `make verify` para confirmar que nada se rompe.
- **Test a ejecutar:** `make verify` completo.

---

### Tarea 1.7 — Popular `source_skill` en `IngestionPipeline` (ADR-0032, parte C)

- **Archivo:** `src/memory/ingestion_pipeline.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Añadir parámetro `source_skill: str | None = None` a la firma de `process_text()`.
  2. En el INSERT a la tabla `memories`, incluir `source_skill` si no es None.
  3. Actualizar todos los callers de `process_text()` para pasar el skill origen:
     - `knowledge_base.py` → `source_skill="knowledge_base"`
     - `memory_summarizer.py` → `source_skill="consolidation"`
     - `global_knowledge_loader.py` → `source_skill="global_knowledge"`
     - tools de TCC → `source_skill="tcc"`
     - tools de Chat → `source_skill="chat"`
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "ingestion" -v`. Verificar que el campo aparece en el registro insertado.

---

### Verificación de Fase 1

- [ ] `make verify` pasa al 100% (ruff + mypy + architecture check).
- [ ] `pytest tests/unit/memory/ -v` — todos los tests existentes pasan.
- [ ] `pytest tests/integration/ -v` — flujo conversacional completo sin errores.
- [ ] Inspeccionar logs de consolidación: confirmar que usa `get_rag_llm()` (Gemini), no `llm` global (Groq).
- [ ] Ejecutar conversación de 15+ mensajes: confirmar que no hay error 413.
- [ ] Verificar que `session_processor.py` no existe: `ls src/memory/session_processor.py` debe retornar error.
- [ ] Verificar que `embedding_cache` recibe hits en la segunda ingesta del mismo texto.

---

## Fase 2 — Arquitectura RAG y Ingesta Atómica

**Estado:** Completado
**Prerrequisito:** Fase 1 completada y verificada.
**Objetivo:** Refactorizar la recuperación de contexto como nodo LangGraph independiente, migrar la ingesta de facts a modo atómico, y desplegar el Reranker basado en API. Al final de esta fase, el RAG es condicional al intent, observable por el orquestador, y recupera hechos precisos en lugar de bloques JSON mezclados.
**Verificación final de fase:** `make verify` pasa. El prompt inyectado en un saludo casual tiene 0 fragmentos de RAG semántico. Los hechos del usuario son recuperables individualmente.

---

### Tarea 2.1 — Añadir `RagContextSnapshot` a `GraphStateV2` (ADR-0031)

- **Archivo:** `src/core/schemas/graph.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Añadir la clase `RagContextSnapshot` como `TypedDict` con `total=False`:
     ```python
     class RagContextSnapshot(TypedDict, total=False):
         semantic_fragments: list[dict]
         graph_fragments: list[dict]
         evolution_note: str | None
         structured_facts: list[dict]
         total_tokens_estimated: int
         retrieved_at: float
         cache_hit: bool
     ```
  2. Añadir en `GraphStateV2`:
     ```python
     rag_context: RagContextSnapshot | None
     ```
  3. El campo es opcional (`None` por defecto) — compatibilidad hacia atrás con todos los nodos existentes garantizada.
- **Consumidores afectados:** Todos los nodos del grafo. Verificar con `grep -r 'GraphStateV2' src/` que ningún nodo falla con el nuevo campo opcional.
- **Test a ejecutar:** `pytest tests/unit/core/ -k "graph" -v`. `pytest tests/integration/ -v`.

---

### Tarea 2.2 — Crear nodo `context_retriever` en el grafo (ADR-0031)

- **Archivo nuevo:** `src/agents/orchestrator/context_retriever.py`
- **Acción:** Crear
- **Descripción técnica:**
  1. Función async `context_retriever_node(state: GraphStateV2) -> GraphStateV2`.
  2. Lógica de ejecución condicional:
     ```python
     routing_meta = state["payload"].get("routing_metadata", {})
     intent = routing_meta.get("intent", "unknown")
     CASUAL_INTENTS = {"casual_greeting", "farewell", "acknowledgement"}

     if intent in CASUAL_INTENTS:
         # Solo cargar evolution_note desde Redis (0ms). Sin búsqueda vectorial.
         evolution_note = await _load_evolution_note(chat_id)
         state["rag_context"] = RagContextSnapshot(
             semantic_fragments=[],
             evolution_note=evolution_note,
             structured_facts=[],
             cache_hit=True,
             retrieved_at=time.time(),
         )
         return state
     ```
  3. Para intents no casuales: ejecutar Two-Stage Retrieval completo (ADR-0030), cargar facts atómicos con confianza ≥ 0.7, estimar tokens, aplicar guardia `MAX_RAG_TOKENS` (default 2000 tokens, configurable en settings).
  4. Depositar `RagContextSnapshot` en `state["rag_context"]`.
  5. Inyección de dependencias: recibir `VectorMemoryManager`, `RedisClient` como argumentos funcionales (no instanciar internamente).
- **Consumidores:** `src/agents/orchestrator/graph_builder.py` — debe añadir el nodo al grafo y conectarlo en el orden correcto.
- **Test a ejecutar:** `pytest tests/unit/core/ -k "context_retriever" -v` (nuevo test unitario de este nodo).

---

### Tarea 2.3 — Registrar `context_retriever` en `graph_builder.py`

- **Archivo:** `src/agents/orchestrator/graph_builder.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Importar `context_retriever_node` desde el nuevo módulo.
  2. Añadir el nodo al grafo: `graph.add_node("context_retriever", context_retriever_node)`.
  3. Ajustar las aristas del grafo:
     - Después de `meta_router` / `enhanced_router`: añadir arista a `context_retriever`.
     - Desde `context_retriever`: aristas hacia cada nodo de especialista (chat, tcc, etc.).
  4. Verificar que el flujo completo sigue siendo: `meta_router → enhanced_router → context_retriever → specialist → chain_router → END`.
- **Test a ejecutar:** `pytest tests/integration/ -v` — el flujo completo de mensajería debe funcionar.

---

### Tarea 2.4 — Refactorizar tools de especialistas para leer `rag_context` del estado (ADR-0031)

- **Archivos:** `src/personality/skills/chat/tools.py`, `src/personality/skills/tcc/tools.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Eliminar las funciones `_get_chat_rag_context()` y `_get_cbt_rag_context()`.
  2. En `conversational_chat_tool()` y `cbt_therapeutic_guidance_tool()`: leer `state["rag_context"]` directamente.
  3. Formatear `RagContextSnapshot` para inyección al prompt:
     - `semantic_fragments`: renderizar como bullets con contenido.
     - `evolution_note`: inyectar directamente en la sección de Memoria de Largo Plazo.
     - `structured_facts`: formatear como pares clave-valor filtrados por confianza ≥ 0.7.
  4. Si `rag_context` es `None` (no debería ocurrir en producción, pero como degradación suave): construir el contexto vacío sin fallar.
- **Test a ejecutar:** `pytest tests/unit/ -k "chat_tool or cbt_tool" -v`.

---

### Tarea 2.5 — Migrar `KnowledgeBaseManager` a ingesta atómica (ADR-0032, parte A)

- **Archivo:** `src/memory/knowledge_base.py`
- **Acción:** Modificar (refactorización del método `save_knowledge`)
- **Descripción técnica:**
  1. Crear método `save_knowledge_atomic(knowledge_dict: dict, chat_id: str, source_skill: str) -> None`:
     - Definir mapeador heurístico de `fact_key → domain`:
       ```python
       DOMAIN_MAP = {
           "presupuesto": "finance", "gasto": "finance", "ingreso": "finance",
           "entrenamiento": "fitness", "sentadilla": "fitness", "peso": "fitness",
           "calorias": "nutrition", "dieta": "nutrition",
           "estres": "psychology", "ansiedad": "psychology", "meta": "psychology",
           # ... expandir según vocabulario del extractor
       }
       def _infer_domain(key: str) -> str:
           key_lower = key.lower()
           for keyword, domain in DOMAIN_MAP.items():
               if keyword in key_lower:
                   return domain
           return "general"
       ```
     - Por cada `(key, value)` en el dict: construir texto `f"{key}: {value}"`, llamar a `IngestionPipeline.process_text()` con metadatos `{"domain": domain, "hierarchy_level": 4, "fact_key": key}` y `source_skill=source_skill`.
  2. Reemplazar las llamadas a `save_knowledge()` por `save_knowledge_atomic()` en `consolidation_worker.py` y `services/incremental_extractor.py`.
  3. Refactorizar el fallback de carga de bóveda (`knowledge_base.py:59-75`): en lugar de buscar un único registro JSON, hacer `SELECT content, metadata FROM memories WHERE chat_id=? AND memory_type='fact' AND is_active=1 ORDER BY created_at DESC` y reconstruir el dict desde los registros atómicos.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "knowledge_base" -v`. Añadir test que verifique que un dict con 5 facts genera 5 registros independientes en la DB.

---

### Tarea 2.6 — Script de migración de facts existentes (ADR-0032, parte A, legacy)

- **Archivo nuevo:** `scripts/migrate_facts_to_atomic.py`
- **Acción:** Crear
- **Descripción técnica:**
  1. Script one-shot, idempotente (puede ejecutarse múltiples veces sin duplicar datos).
  2. Query: `SELECT id, chat_id, content FROM memories WHERE memory_type='fact' AND is_active=1 AND metadata NOT LIKE '%"fact_key"%'` — selecciona todos los facts que son blobs JSON (no atómicos).
  3. Por cada registro: parsear el JSON, ingestar cada entrada atómicamente con `save_knowledge_atomic()`.
  4. Tras ingestar exitosamente todos los entries: marcar el registro original como `is_active=0` con `UPDATE memories SET is_active=0 WHERE id=?`.
  5. Log estructurado de progreso: N registros migrados, N hechos atómicos creados.
  6. Añadir entrada en `Makefile`: `make migrate-facts`.
- **Prerrequisito:** Tarea 2.5 completada.
- **Ejecución:** Una única vez en producción después del deploy de Fase 2.

---

### Tarea 2.7 — Implementar Reranker basado en Gemini API

- **Archivo nuevo:** `src/memory/reranker.py`
- **Acción:** Crear
- **Descripción técnica:**
  1. Clase `SemanticReranker` con método `async rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]`.
  2. Construir prompt estructurado:
     ```
     Dada la pregunta: "{query}"
     Evalúa la relevancia de cada fragmento en una escala 0.0-1.0.
     Fragmentos: [lista numerada de contenidos]
     Responde SOLO con JSON: [{"index": N, "relevance": 0.X}, ...]
     ```
  3. Llamar a `get_rag_llm()` (Gemini Flash) con el prompt.
  4. Parsear la respuesta JSON, reordenar los candidatos por `relevance` descendente, retornar `[:top_k]`.
  5. Degradación suave: si la llamada LLM falla o el JSON es inválido, retornar los candidatos originales sin reranking (con log de advertencia).
  6. Integrar en `context_retriever_node` (Tarea 2.2): aplicar reranking sobre los `semantic_fragments` antes de incluirlos en `RagContextSnapshot`. Solo activar si `len(semantic_fragments) > top_k`.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "rerank" -v` (mockear la llamada LLM).

---

### Tarea 2.8 — Ampliar Redis Cache para Nota Evolutiva (ADR-0029 complemento)

- **Archivos:** `src/memory/consolidation_worker.py`, `src/memory/services/memory_summarizer.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Tras generar la Nota de Progreso Analítica en `consolidation_worker.py`, guardarla en Redis con la clave `chat:evolution_note:{chat_id}` y TTL de 24 horas (no reemplazar la clave `chat:summary:{chat_id}` existente — son datos distintos).
  2. En `context_retriever_node` (Tarea 2.2): intentar leer `chat:evolution_note:{chat_id}` como primera opción para `evolution_note`. Si no existe (miss), usar `chat:summary:{chat_id}` como fallback.
  3. La Nota Evolutiva es más rica que el resumen: incluye correlaciones entre dominios y estado de progreso multi-área.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "consolidat" -v`.

---

### Tarea 2.9 — Corregir Namespaces: `"user"` → `"user_{chat_id}"`

- **Archivos:** `src/memory/ingestion_pipeline.py`, `src/memory/repositories/memory_repo.py`
- **Acción:** Modificar
- **Descripción técnica:**
  1. En `IngestionPipeline.process_text()`: añadir parámetro `namespace: str | None = None`. Si no se provee, calcular `f"user_{chat_id}"` como default para contenido de usuario. Para contenido global, usar `"global"` (sin cambio).
  2. Actualizar todos los callers de `process_text()` para pasar `namespace` correctamente.
  3. No migrar los registros existentes en esta fase — los namespaces viejos (`"user"`) seguirán funcionando porque el aislamiento real es por `chat_id`. La migración de namespace es cosmética y puede hacerse de forma incremental.
  4. Añadir nota en código: `# namespace legacy "user" aún válido; nuevos registros usan "user_{chat_id}"`.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "ingestion or namespace" -v`.

---

### Verificación de Fase 2

- [ ] `make verify` pasa al 100%.
- [ ] `pytest tests/ -v` — todos los tests pasan.
- [ ] Enviar un saludo ("Hola"): confirmar en logs que `rag_context.semantic_fragments` es `[]`.
- [ ] Enviar una pregunta clínica: confirmar que `rag_context.semantic_fragments` contiene fragmentos relevantes.
- [ ] Ingestar 5 facts en la DB: verificar que existen 5 registros independientes con `memory_type='fact'` y `fact_key` en metadata.
- [ ] Ejecutar `scripts/migrate_facts_to_atomic.py` en DB de desarrollo: verificar N registros migrados, 0 errores.
- [ ] Verificar que `evolution_note` en Redis se actualiza tras una sesión de consolidación.

---

## Fase 3 — Grafo Relacional y Ontología Jerárquica

**Estado:** Completado
**Prerrequisito:** Fase 2 completada y verificada. ADRs 0031, 0032 y 0033 aprobados.
**Objetivo:** Implementar el schema de grafo completo (`parent_id`, `memory_edges`), el pipeline de ingesta jerárquica con LLM, y el Graph-RAG con búsqueda multi-salto. Al final de esta fase, MAGI puede razonar sobre conexiones entre dominios (fitness ↔ psicología ↔ finanzas).
**Verificación final de fase:** `make verify` pasa. Una consulta analítica retorna fragmentos de al menos 2 dominios distintos conectados por `memory_edges`. El schema de DB tiene `parent_id` y `memory_edges`.

---

### Tarea 3.1 — Backup de DB de producción

- **Acción:** Operacional (prerrequisito de seguridad)
- **Descripción técnica:**
  1. Antes de cualquier modificación de schema: ejecutar `make backup` o equivalente para generar un snapshot de `storage/aegen_memory.db`.
  2. Verificar que el backup es legible: `sqlite3 backup.db "SELECT COUNT(*) FROM memories;"`.
  3. Documentar la fecha y tamaño del backup en un comentario en `migration.py`.
- **No continuar con Tarea 3.2 sin backup verificado.**

---

### Tarea 3.2 — Añadir `parent_id` a `memories` y crear `memory_edges` (ADR-0033)

- **Archivo:** `src/memory/schema.sql`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Añadir columna a `memories` (retrocompatible — nullable):
     ```sql
     ALTER TABLE memories ADD COLUMN parent_id INTEGER REFERENCES memories(id) ON DELETE CASCADE;
     CREATE INDEX IF NOT EXISTS idx_memories_parent ON memories(parent_id) WHERE parent_id IS NOT NULL;
     ```
  2. Crear tabla `memory_edges`:
     ```sql
     CREATE TABLE IF NOT EXISTS memory_edges (
         id            INTEGER PRIMARY KEY AUTOINCREMENT,
         origen_id     INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
         destino_id    INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
         tipo_relacion TEXT NOT NULL CHECK(tipo_relacion IN (
             'correlaciona_con', 'causa', 'resuelve', 'contradice', 'refuerza'
         )),
         peso          REAL NOT NULL DEFAULT 1.0 CHECK(peso >= 0.0 AND peso <= 1.0),
         evidencia     TEXT,
         created_by    TEXT NOT NULL,
         created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );
     CREATE INDEX IF NOT EXISTS idx_edges_origen  ON memory_edges(origen_id);
     CREATE INDEX IF NOT EXISTS idx_edges_destino ON memory_edges(destino_id);
     CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair ON memory_edges(origen_id, destino_id, tipo_relacion);
     ```
  3. Añadir estas sentencias en `migration.py` como migraciones idempotentes (usar `IF NOT EXISTS` y manejo de `OperationalError` para `ALTER TABLE` en SQLite).
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "schema or migration" -v`. Verificar que la migración es idempotente (ejecutar dos veces sin error).

---

### Tarea 3.3 — Crear `graph_search.py` con búsqueda multi-salto (ADR-0033)

- **Archivo nuevo:** `src/memory/graph_search.py`
- **Acción:** Crear
- **Descripción técnica:**
  1. Función `async expand_with_edges(db, seed_ids: list[int], max_hops: int = 2, relation_types: list[str] | None = None) -> list[dict]`.
  2. Implementar CTE recursiva de SQLite (ver query en ADR-0033).
  3. Para cada `memory_id` del sub-grafo, hacer JOIN con `memories` para obtener `content`, `domain`, `hierarchy_level`, `metadata`.
  4. Retornar lista de dicts con `{memory_id, content, domain, relevance_weight, hop_distance}`.
  5. Límite hard de `max_hops=2` como valor máximo permitido — no exponer como configurable externamente para evitar queries lentas accidentales.
  6. Si `memory_edges` está vacía (primeras semanas post-deploy): retornar lista vacía sin error.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "graph_search" -v` (nuevo test con DB fixture que incluye edges precargados).

---

### Tarea 3.4 — Integrar Graph-RAG en `context_retriever_node`

- **Archivo:** `src/agents/orchestrator/context_retriever.py`
- **Acción:** Modificar (añadir expansión de grafo condicional)
- **Descripción técnica:**
  1. Definir `ANALYTICAL_INTENTS = {"life_review", "pattern_analysis", "cross_domain_query"}`.
  2. Si `intent in ANALYTICAL_INTENTS`:
     - Tomar los `memory_id` de los `semantic_fragments` ya recuperados como semilla.
     - Llamar a `expand_with_edges(seed_ids=[...], max_hops=2)`.
     - Añadir los resultados a `state["rag_context"]["graph_fragments"]`.
  3. Para todos los demás intents: `graph_fragments = []`.
  4. El reranker (Tarea 2.7) debe operar sobre `semantic_fragments + graph_fragments` combinados.
- **Test a ejecutar:** `pytest tests/unit/core/ -k "context_retriever" -v`. Añadir caso de test con intent analítico.

---

### Tarea 3.5 — Actualizar `ConsolidationWorker` para generar `memory_edges`

- **Archivo:** `src/memory/consolidation_worker.py`
- **Acción:** Modificar (añadir generación de edges al final del pipeline)
- **Descripción técnica:**
  1. Tras la generación de la Nota de Progreso Analítica, añadir paso opcional `_generate_edges()`:
     - Prompt a Gemini Flash con los events atómicos de la sesión y las memorias existentes de los últimos 7 días.
     - El LLM responde con JSON de edges a crear:
       ```json
       [
         {"origen_fact_key": "calorias_deficit", "destino_fact_key": "irritabilidad", "tipo": "correlaciona_con", "peso": 0.8, "evidencia": "Usuario reportó irritabilidad los mismos días de mayor déficit calórico"}
       ]
       ```
     - Por cada edge: resolver `fact_key → memory_id` con query `WHERE metadata LIKE '%"fact_key": "X"%'`, insertar en `memory_edges` con `INSERT OR IGNORE` (el índice UNIQUE previene duplicados).
  2. Todo el bloque `_generate_edges()` está en `try/except` — si falla, se loggea y la consolidación continúa sin edges. Los edges son un enriquecimiento, no un requisito.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "consolidat" -v`.

---

### Tarea 3.6 — Implementar pipeline de ingesta jerárquica (Pilar I, fuentes externas)

- **Archivo nuevo:** `src/memory/semantic_chunker.py`
- **Archivos modificados:** `src/memory/ingestion_pipeline.py`, `src/memory/global_knowledge_loader.py`
- **Acción:** Crear + Modificar
- **Descripción técnica:**
  1. `semantic_chunker.py`: nuevo chunker que usa Gemini Flash para segmentar texto externo en bloques semánticos coherentes (no por tamaño fijo):
     - Pre-filtro heurístico primero: eliminar líneas que matcheen patrones de ruido (`r"suscríbete|subscribe|^\s*eh+\s*$|\d{2}:\d{2}:\d{2}"` y similares).
     - Llamada a Gemini con prompt de segmentación: dividir en bloques Nivel 3 (técnicas) y Nivel 4 (fragmentos purificados).
     - Retornar lista de `{"content": str, "hierarchy_level": int, "domain": str}`.
  2. `ingestion_pipeline.py`: añadir branch de ingesta para fuentes externas (`source_type="global"` o `namespace="global"`):
     - Usar `SemanticChunker` en lugar de `RecursiveChunker`.
     - Guardar el bloque Nivel 3 como `parent_id=None` con `memory_type="document_parent"` (no vectorizado).
     - Por cada fragmento Nivel 4: guardar con `parent_id=<id_nivel3>` y vectorizar (siguiendo ADR-0028 extendido).
  3. `global_knowledge_loader.py`: pasar `use_semantic_chunker=True` para PDFs y transcripciones. Mantener `RecursiveChunker` para fuentes de usuario (mensajes de chat) donde la velocidad es crítica.
- **Test a ejecutar:** `pytest tests/unit/memory/ -k "ingestion or chunker" -v`.

---

### Tarea 3.7 — Actualizar Plan Maestro Estratégico

- **Archivo:** `docs/planes/PLAN-MAESTRO-ESTRATEGICO.md`
- **Acción:** Modificar
- **Descripción técnica:**
  1. Marcar B.3 (Smart Decay) como completado al finalizar Fase 1, Tarea 1.3.
  2. Añadir referencia a este plan en el Bloque B.
  3. Añadir tarea B.4: "Arquitectura de Memoria Asociativa Multiresolución (Graph-RAG)" como completada al finalizar Fase 3.

---

### Verificación de Fase 3

- [ ] `make verify` pasa al 100%.
- [ ] `pytest tests/ -v` — todos los tests pasan incluyendo los nuevos.
- [ ] `sqlite3 storage/aegen_memory.db ".schema"` — confirmar que `memory_edges` existe con sus índices.
- [ ] `sqlite3 storage/aegen_memory.db "SELECT COUNT(*) FROM memory_edges;"` — tras 2+ sesiones de consolidación, debe haber > 0 edges.
- [ ] Consulta analítica de test: `expand_with_edges(seed_ids=[X], max_hops=2)` retorna memorias de al menos 2 dominios distintos.
- [ ] Ingesta de un PDF de prueba: verificar que se generan chunks con `hierarchy_level=3` y `hierarchy_level=4`, vinculados por `parent_id`.

---

## Seguimiento de Tareas

### Fase 1 — Estabilidad de Producción
- [ ] 1.1 Migrar `MemorySummarizer` a Gemini
- [ ] 1.2 Migrar `EvolutionDetector` a Gemini
- [ ] 1.3 Implementar Time Decay en `HybridSearch`
- [ ] 1.4 Filtrado por `context_type` en tools de especialistas
- [ ] 1.5 Activar Embedding Cache con índice
- [ ] 1.6 Eliminar `session_processor.py`
- [ ] 1.7 Popular `source_skill` en `IngestionPipeline`
- [ ] Verificación completa de Fase 1

### Fase 2 — Arquitectura RAG y Ingesta Atómica
- [ ] 2.1 Añadir `RagContextSnapshot` a `GraphStateV2`
- [ ] 2.2 Crear nodo `context_retriever`
- [ ] 2.3 Registrar `context_retriever` en `graph_builder.py`
- [ ] 2.4 Refactorizar tools de especialistas para leer `rag_context`
- [ ] 2.5 Migrar `KnowledgeBaseManager` a ingesta atómica
- [ ] 2.6 Script de migración de facts existentes
- [ ] 2.7 Implementar Reranker basado en Gemini API
- [ ] 2.8 Ampliar Redis Cache para Nota Evolutiva
- [ ] 2.9 Corregir namespaces `"user"` → `"user_{chat_id}"`
- [ ] Verificación completa de Fase 2

### Fase 3 — Grafo Relacional y Ontología Jerárquica
- [ ] 3.1 Backup de DB de producción
- [ ] 3.2 Añadir `parent_id` y crear `memory_edges` en schema
- [ ] 3.3 Crear `graph_search.py` con búsqueda multi-salto
- [ ] 3.4 Integrar Graph-RAG en `context_retriever_node`
- [ ] 3.5 Actualizar `ConsolidationWorker` para generar edges
- [ ] 3.6 Implementar pipeline de ingesta jerárquica (fuentes externas)
- [ ] 3.7 Actualizar Plan Maestro Estratégico
- [ ] Verificación completa de Fase 3

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos

- **Agentes paralelos:** Las Tareas 1.1 y 1.2 pueden ejecutarse en paralelo (archivos distintos). Las Tareas 1.3, 1.4, 1.5, 1.6, 1.7 también son independientes entre sí dentro de Fase 1.
- **Calibración de λ:** El valor `0.01` de `MEMORY_DECAY_LAMBDA` es una estimación inicial. Debe monitorizarse mediante métricas de relevancia de los primeros 30 días post-deploy y ajustarse si los usuarios reportan que MAGI "olvida" cosas relevantes demasiado rápido.
- **Costo Gemini en Fase 3:** El `SemanticChunker` (Tarea 3.6) hace una llamada LLM por bloque de texto externo. Implementar un límite de rate en el `GlobalKnowledgeLoader` para no saturar la cuota de Gemini en ingestas masivas (ej. semáforo async con máximo 5 llamadas concurrentes).
- **Grafo vacío al inicio:** `memory_edges` estará vacía al hacer el deploy de Fase 3. El Graph-RAG retornará listas vacías hasta que el `ConsolidationWorker` genere los primeros edges. Esto es comportamiento esperado y no un error.
- **Compatibilidad de `ALTER TABLE` en SQLite:** SQLite solo soporta `ADD COLUMN` en `ALTER TABLE`, no `DROP COLUMN` ni `RENAME COLUMN` en versiones antiguas. El `parent_id` se añade como nullable — la migración es segura y reversible (se puede marcar `is_active=0` en columna no usada, pero no eliminar sin recrear la tabla).
