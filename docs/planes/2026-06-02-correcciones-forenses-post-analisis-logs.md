# PLAN: Correcciones Forenses Post-Análisis de Logs (Jun 2026)

> **Instrucciones para Agentes:**
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Propuesto
- **Fecha:** 2026-06-02
- **Razón de Creación:** Corrección de Error + Refactorización
- **ADR Relacionado:** adr/ADR-0039-intent-meta-feedback.md (para Fase 5)
- **Objetivo General:** Resolver los 5 problemas identificados en el análisis forense de logs del período 2026-05-31 a 2026-06-02, usando cambios mínimos alineados con los patrones existentes del codebase.

---

## Resumen Ejecutivo

El análisis forense de logs de producción identificó 7 problemas. Tras lectura exhaustiva del código fuente, 5 requieren acción inmediata y 2 se difieren por falta de datos. Los problemas son:

1. **Bug activo:** `_check_edges_exist` llama `store.execute()` que no existe en `SQLiteStore` — Graph-RAG silenciosamente deshabilitado.
2. **Degradación de latencia:** `ChatGroq(max_retries=3)` causa 3 retries con backoff antes de activar el fallback nativo `.with_fallbacks()` — latencia de 8s a 48s.
3. **Ruido en logs:** `logger.info("Health check requested.")` cada 60s genera ~1400 entradas en 36h.
4. **Config incompleta:** `ADMIN_CHAT_ID` no validado ni advertido correctamente en producción.
5. **Feedback loop terapéutico:** `therapeutic_session.py` trata el meta-feedback del usuario ("tus respuestas son muy largas") como "resistencia terapéutica" y lo fuerza de vuelta a `cbt_specialist`.

**Impacto si NO se hace nada:** El Graph-RAG nunca funcionará, la latencia seguirá degradando bajo carga, y los usuarios del CBT no podrán ajustar el estilo de respuesta.

---

## Análisis de Impacto

### Dependencias afectadas

**Fase 1 (`context_retriever.py`):**
- Consumidores: `graph_builder.py:69` (importa `context_retriever_node`)
- No modifica interfaz — solo cambia implementación interna de `_check_edges_exist`

**Fase 2 (`engine.py`):**
- Consumidores: `routing_analyzer.py:29` (importa `llm`), `status.py:58` (importa `check_llm_health`)
- El singleton `llm` no cambia. Solo se modifica `max_retries` y `timeout` en las factorías internas.

**Fase 5 (`routing_models.py`, `intent_patterns_data.py`, `therapeutic_session.py`):**
- `routing_models.IntentType` es consumido por: `enhanced_router.py`, `routing_enhancer.py`, `routing_decision_builder.py`, `routing_patterns.py`, `therapeutic_session.py`, `intent_patterns_data.py`
- Añadir un valor al enum `IntentType` es backward-compatible (no rompe consumers existentes)
- `SESSION_BREAKING_INTENTS` solo es consumido por `enhanced_router.py:115`

### Cobertura de tests existente
- Verificar con `grep -r '_check_edges_exist\|IntentType\|therapeutic_session' tests/` antes de implementar
- Crear tests para cada cambio antes de modificar el código

### Verificación del pipeline
- Fase 5 toca `src/agents/orchestrator/routing/` → trazar flujo: Telegram → Webhook → EventProcessor → MasterOrchestrator → EnhancedRouter → therapeutic_session → specialist

---

## Fase 1: Fix `_check_edges_exist` (Bug activo)

### Objetivo
Eliminar el warning `'SQLiteStore' object has no attribute 'execute'` y habilitar la verificación de aristas en Graph-RAG.

### Justificación
El bug deshabilita silenciosamente la expansión de grafo (Graph-RAG ADR-0033/0034) en cada request no-casual. La función `graph_search.py` ya implementa el patrón correcto — este fix alinea `_check_edges_exist` con ese patrón.

### Cambios Previstos

- **Módulo/Archivo:** `src/agents/orchestrator/context_retriever.py:57-82`
  - **Acción:** Modificar
  - **Descripción:** Reemplazar `store.execute(query, params)` por `db = await store.get_db()` + `async with db.execute(query, params) as cursor`
  - **Consumidores:** `context_retriever_node` (usado como nodo LangGraph en `graph_builder.py:69`)

**Código exacto del cambio:**

```python
# ANTES (líneas 75-78):
        params = memory_ids + memory_ids
        result = await store.execute(query, params)
        rows = await result.fetchone()
        return rows is not None

# DESPUÉS:
        params = memory_ids + memory_ids
        db = await store.get_db()
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row is not None
```

### Verificación de Fase

**Step 1:** Verificar que el cambio compila:
```bash
make verify
```
Expected: PASS (0 errores ruff, 0 errores mypy)

**Step 2:** Commit:
```bash
git add src/agents/orchestrator/context_retriever.py
git commit -m "fix(memory): usar get_db() en _check_edges_exist (alinear con graph_search.py)"
```

- [x] Usa inyección de dependencias (recibe `store` como argumento)
- [x] Maneja errores con degradación suave (try/except retorna False)
- [x] No genera cadena de imports eager
- [x] No modifica schema

---

## Fase 2: Reducir latencia de rate limiting

### Objetivo
Reducir la latencia máxima de orquestación de ~48s a ~12s cuando Groq aplica rate limiting.

### Justificación
`ChatGroq(max_retries=3)` reintenta 3 veces con los headers `Retry-After` de Groq (6s, 40s, 4s = 50s) antes de lanzar excepción y activar `.with_fallbacks()`. Reducir a `max_retries=1` activa el fallback tras 1 retry, preservando la resiliencia sin la penalización de latencia.

### Cambios Previstos

- **Módulo/Archivo:** `src/core/engine.py:28-47`
  - **Acción:** Modificar
  - **Descripción:** Cambiar `max_retries=3` a `max_retries=1` y `timeout=60` a `timeout=30` en `_create_groq_llm`. Cambiar `max_retries=3` a `max_retries=1` y `timeout=60` a `timeout=30` en `_create_openrouter_llm`.
  - **Consumidores:** `get_fast_llm()`, `get_analytical_llm()`, singleton `llm` en línea 140

**Código exacto del cambio:**

```python
# _create_openrouter_llm (línea 18-25):
    return ChatOpenAI(
        model=target_model,
        temperature=0.7,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        max_retries=1,   # Era 3
        timeout=30,       # Era 60
    )

# _create_groq_llm (línea 41-47):
    return ChatGroq(
        model=target_model,
        temperature=0.7,
        api_key=api_key,
        max_retries=1,   # Era 3
        timeout=30,       # Era 60
    )
```

### Verificación de Fase

**Step 1:** `make verify`
**Step 2:** Commit:
```bash
git add src/core/engine.py
git commit -m "perf(engine): reducir max_retries a 1 para activar fallback más rápido"
```

- [x] No modifica interfaz pública
- [x] Degradación suave preservada (fallback sigue existiendo)
- [x] No afecta imports

---

## Fase 3: Reducir ruido de health checks en logs

### Objetivo
Eliminar ~1400 entradas de log redundantes por período de 36h.

### Justificación
`logger.info("Health check requested.")` se ejecuta cada 60s por Docker healthcheck. No aporta valor operacional en INFO — solo útil para debugging.

### Cambios Previstos

- **Módulo/Archivo:** `src/api/routers/status.py:99`
  - **Acción:** Modificar
  - **Descripción:** Cambiar `logger.info` a `logger.debug`
  - **Consumidores:** Ninguno (es un log statement)

**Código exacto:**

```python
# ANTES:
    logger.info("Health check requested.")

# DESPUÉS:
    logger.debug("Health check requested.")
```

### Verificación de Fase

**Step 1:** `make verify`
**Step 2:** Commit:
```bash
git add src/api/routers/status.py
git commit -m "chore(status): reducir health check log a DEBUG"
```

---

## Fase 4: Validación de ADMIN_CHAT_ID

### Objetivo
Emitir warning visible al arranque si `ADMIN_CHAT_ID` no está configurado en producción.

### Justificación
Sin `ADMIN_CHAT_ID`, el `AdminNotificator` se deshabilita silenciosamente. El warning existente se pierde entre miles de líneas de log. Mover la validación al `model_validator` de Pydantic la hace visible al arranque.

### Cambios Previstos

- **Módulo/Archivo:** `src/core/config/base.py:105-114`
  - **Acción:** Modificar
  - **Descripción:** Añadir validación warn-level para `ADMIN_CHAT_ID` en producción
  - **Consumidores:** Todo el sistema (settings es global)

**Código exacto:**

```python
# DESPUÉS del bloque de required_secrets (después de línea 113):
        # Recommended but non-critical
        recommended = ["ADMIN_CHAT_ID"]
        missing_rec = [k for k in recommended if not getattr(self, k)]
        if missing_rec:
            import warnings
            warnings.warn(
                f"Recommended production settings not configured: "
                f"{', '.join(missing_rec)}. Some features will be disabled.",
                stacklevel=2,
            )
```

### Verificación de Fase

**Step 1:** `make verify`
**Step 2:** Commit:
```bash
git add src/core/config/base.py
git commit -m "chore(config): warn si ADMIN_CHAT_ID falta en producción"
```

---

## Fase 5: Romper el feedback loop terapéutico (requiere ADR-0039)

### Objetivo
Permitir que los usuarios en sesión CBT puedan ajustar el estilo de respuesta de MAGI sin quedar atrapados en el loop de "resistencia terapéutica".

### Justificación
`therapeutic_session.py` clasifica TODO intento de salir de CBT (excepto TOPIC_SHIFT) como resistencia terapéutica. El feedback sobre estilo ("tus respuestas son muy largas") se reclasifica como vulnerabilidad y se reenvía a CBT, creando un loop negativo. La infraestructura para persistir y aplicar preferencias de estilo ya existe (StyleAnalyzer, prompt_builder, profile_manager) pero no se alimenta.

### Cambios Previstos

**5a.**
- **Módulo/Archivo:** `src/core/routing_models.py:15-29`
  - **Acción:** Modificar
  - **Descripción:** Añadir `META_FEEDBACK = "meta_feedback"` al enum `IntentType`
  - **Consumidores:** `enhanced_router.py`, `routing_enhancer.py`, `routing_decision_builder.py`, `routing_patterns.py`, `therapeutic_session.py`, `intent_patterns_data.py`

```python
class IntentType(str, Enum):
    # ... existentes ...
    META_FEEDBACK = "meta_feedback"
```

**5b.**
- **Módulo/Archivo:** `src/agents/orchestrator/routing/intent_patterns_data.py`
  - **Acción:** Modificar
  - **Descripción:** Añadir patterns para `IntentType.META_FEEDBACK`
  - **Consumidores:** `routing_patterns.py` (PatternExtractor, IntentValidator)

```python
IntentType.META_FEEDBACK: [
    "muy largo", "muy larga", "muy largas", "muy largos",
    "demasiado largo", "demasiado larga",
    "respuestas más cortas", "sé más breve",
    "pareces un check list", "checklist",
    "no me gusta como respondes", "cambia tu estilo",
    "menos formal", "más directo", "sin bullets",
    "no uses listas", "habla normal", "responde más corto",
    "muy formal", "demasiado formal",
],
```

**5c.**
- **Módulo/Archivo:** `src/agents/orchestrator/routing/therapeutic_session.py:20`
  - **Acción:** Modificar
  - **Descripción:** Añadir `IntentType.META_FEEDBACK` a `SESSION_BREAKING_INTENTS`
  - **Consumidores:** `enhanced_router.py:115` (vía `should_maintain_therapeutic_session`)

```python
# ANTES:
SESSION_BREAKING_INTENTS = {IntentType.TOPIC_SHIFT}

# DESPUÉS:
SESSION_BREAKING_INTENTS = {IntentType.TOPIC_SHIFT, IntentType.META_FEEDBACK}
```

**5d.**
- **Módulo/Archivo:** `src/agents/orchestrator/routing/routing_enhancer.py`
  - **Acción:** Modificar (si `SpecialistMapper.map_intent_to_specialist` no mapea META_FEEDBACK)
  - **Descripción:** Verificar que META_FEEDBACK mapee a `chat_specialist` por defecto
  - **Consumidores:** `routing_analyzer.py` (vía `RoutingEnhancer.enhance_decision`)

**5e.**
- **Módulo/Archivo:** `src/agents/orchestrator/routing/routing_prompts.py`
  - **Acción:** Modificar
  - **Descripción:** Añadir instrucción en el prompt de routing para que el LLM reconozca meta-feedback como intent distinto a vulnerabilidad
  - **Consumidores:** `routing_analyzer.py` (vía `build_routing_prompt`)

### Verificación de Fase

**Step 1:** Verificar que el enum extendido no rompe consumers:
```bash
grep -r 'IntentType\.' src/ | grep -v __pycache__ | grep -v '.pyc'
```
Verificar que ningún consumer hace matching exhaustivo sin default.

**Step 2:** `make verify`

**Step 3:** Commit:
```bash
git add src/core/routing_models.py \
  src/agents/orchestrator/routing/intent_patterns_data.py \
  src/agents/orchestrator/routing/therapeutic_session.py \
  src/agents/orchestrator/routing/routing_enhancer.py \
  src/agents/orchestrator/routing/routing_prompts.py \
  adr/ADR-0039-intent-meta-feedback.md
git commit -m "feat(routing): añadir IntentType.META_FEEDBACK para romper loop terapéutico (ADR-0039)"
```

- [x] Usa inyección de dependencias
- [x] Degradación suave (si META_FEEDBACK no matchea, fallback a CHAT sigue funcionando)
- [x] No genera imports nuevos
- [x] Modifica schema IntentType (backward-compatible — solo añade valor)

---

## Seguimiento de Tareas

- [ ] Fase 1: Fix `_check_edges_exist`
- [ ] Fase 2: Reducir `max_retries` en Groq/OpenRouter
- [ ] Fase 3: Health check log → DEBUG
- [ ] Fase 4: Validación ADMIN_CHAT_ID
- [ ] Fase 5a: Añadir IntentType.META_FEEDBACK
- [ ] Fase 5b: Añadir patterns meta-feedback
- [ ] Fase 5c: Añadir META_FEEDBACK a SESSION_BREAKING_INTENTS
- [ ] Fase 5d: Verificar/ajustar mapeo en routing_enhancer
- [ ] Fase 5e: Actualizar routing prompt
- [ ] Fase 5f: Escribir ADR-0039
- [ ] Ejecutar `make verify` final

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|

---

## Notas y Riesgos

1. **Fase 2 — Efecto en fallback timing:** Reducir `max_retries=1` significa que un error transitorio de Groq (no rate limit) activaría el fallback inmediatamente. Esto es aceptable porque el fallback (OpenRouter) es funcional, y la ganancia de latencia (50s → 10s) supera el riesgo de usar el fallback innecesariamente.

2. **Fase 5 — Falsos positivos de META_FEEDBACK:** Los patterns como "muy largo" podrían matchear en contextos no relacionados ("el camino fue muy largo"). Mitigación: el LLM routing analyzer tiene contexto conversacional completo y debería distinguir. Los patterns solo boostean confianza, no son determinísticos.

3. **Fase 5 — Interacción con ADR-0024 (Protección Terapéutica):** Añadir META_FEEDBACK a SESSION_BREAKING_INTENTS debilita ligeramente la protección de ADR-0024. Esto es intencional — el feedback de estilo NO es resistencia terapéutica y tratarlo así genera frustración en el usuario. El documento ADR-0039 lo explica.

4. **Dependencia entre fases:** Las fases 1-4 son independientes entre sí. La fase 5 es independiente de 1-4. Se pueden ejecutar en cualquier orden o en paralelo.

5. **No se crean archivos nuevos.** Todos los cambios son modificaciones a archivos existentes + 1 ADR nuevo.
