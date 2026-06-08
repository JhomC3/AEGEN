# PLAN: Fix Bugs Post-Desacoplamiento LLM (Bugs 6–9)

> **Instrucciones para Agentes:**
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos.

- **Estado:** Propuesto
- **Fecha:** 2026-06-08
- **Razón de Creación:** Corrección de Error
- **ADR Relacionado:** N/A — son bugs localizados sin cambios de interfaz ni schemas
- **Objetivo General:** Restaurar funcionalidad completa del sistema en producción corrigiendo 4 bugs identificados en el informe forense post-desacoplamiento LLM

---

## Resumen Ejecutivo

Tras corregir el deadlock de key rotation (Bug 5), el sistema arranca y procesa mensajes, pero **todas las llamadas LLM fallan** con `'AsyncCallbackManager' object is not iterable` (Bug 6). Esto impide que MAGI genere respuestas, extraiga hechos, resuma memoria, o haga reranking. Adicionalmente hay 3 bugs menores: prompt template mal escapado (Bug 8), método inexistente en SQLiteStore (Bug 9), y permisos GCS para backups (Bug 7).

Si no se corrige Bug 6, MAGI es un sistema mudo — recibe mensajes pero nunca responde.

---

## Análisis de Impacto

### Dependencias afectadas

**Bug 6** (`src/core/engine.py:28-29`):
- `src/core/llm_registry.py` → `_enrich_config()` llama a `create_observable_config()` en cada `ainvoke`/`invoke`/`astream`
- Afecta **toda llamada LLM** en el sistema: routing, chat, CBT, fact extraction, memory summarization, reranking, evolution detection
- No modifica schemas ni interfaces

**Bug 8** (`src/memory/consolidation_worker.py:198`):
- Solo afecta `_generate_transversal_edges()` — una función interna del consolidation worker
- No tiene consumidores externos

**Bug 9** (`src/agents/orchestrator/context_retriever.py:77`):
- Solo afecta `_check_edges_exist()` — una función interna del context retriever
- El warning se atrapa con `except Exception` y retorna `False` (degradación suave ya existe)

**Bug 7** (`src/memory/backup.py:26`):
- Configuración de infraestructura (IAM/scopes de GCS)
- No requiere cambio de código; solo logging mejorado para diagnóstico

### Cobertura de tests existente

- `tests/unit/memory/test_worker_edges.py` — cubre `_generate_transversal_edges` (Bug 8)
- `tests/unit/memory/test_graph_rag_activation.py` — cubre `_check_edges_exist` (Bug 9)
- No hay test unitario para `create_observable_config` con `AsyncCallbackManager` (Bug 6)

### Verificación del pipeline

Bug 6 toca `src/core/engine.py` que es usado por `src/core/llm_registry.py` → afecta todo el pipeline desde routing hasta respuesta. Verificar flujo completo post-fix.

---

## Fase 1: Fix Bug 6 — `AsyncCallbackManager` not iterable (CRÍTICO)

### Objetivo
Que `create_observable_config` maneje correctamente `config["callbacks"]` cuando es un `AsyncCallbackManager` en vez de una lista.

### Justificación
Este bug bloquea **todas** las llamadas LLM. Sin este fix, MAGI no puede generar ninguna respuesta.

### Cambios Previstos

- **Módulo:** `src/core/engine.py`
  - **Acción:** Modificar
  - **Líneas:** 24-33
  - **Descripción:** Normalizar `config["callbacks"]` a lista antes de iterar. Si es un `BaseCallbackManager`, extraer sus handlers. Si no es iterable, reemplazar con lista vacía.
  - **Consumidores:** `src/core/llm_registry.py` (via `_enrich_config`)

### Detalle del Fix

El problema está en `src/core/engine.py:24-33`. Cuando LangChain pasa un `RunnableConfig` internamente (por ejemplo al ejecutar una LCEL chain como `prompt | llm`), el campo `callbacks` puede contener un `AsyncCallbackManager` en vez de una `list`.

`ManagedLLM._enrich_config()` hace `dict(config)` que preserva el `AsyncCallbackManager` tal cual. Luego `create_observable_config` intenta iterar sobre él con `for cb in config["callbacks"]`.

**Código actual** (`src/core/engine.py:24-33`):
```python
if "callbacks" not in config:
    config["callbacks"] = []

# Validamos si ya está el handler en callbacks para no duplicar
has_handler = any(
    isinstance(cb, LLMObservabilityHandler) for cb in config["callbacks"]
)
if not has_handler:
    observability_handler = LLMObservabilityHandler(call_type=call_type)
    config["callbacks"].append(observability_handler)
```

**Fix** — Normalizar callbacks a lista:
```python
if "callbacks" not in config:
    config["callbacks"] = []

callbacks = config["callbacks"]

# LangChain puede pasar un CallbackManager en vez de una lista.
# Normalizar a lista para poder iterar y hacer append.
if callbacks is None:
    callbacks = []
elif not isinstance(callbacks, list):
    # BaseCallbackManager / AsyncCallbackManager → extraer handlers
    callbacks = list(getattr(callbacks, "handlers", []))

config["callbacks"] = callbacks

has_handler = any(
    isinstance(cb, LLMObservabilityHandler) for cb in callbacks
)
if not has_handler:
    config["callbacks"].append(LLMObservabilityHandler(call_type=call_type))
```

### Step 1: Escribir test que reproduzca el bug

**Archivo:** `tests/unit/core/test_observable_config.py`

```python
"""Test que reproduce Bug 6: AsyncCallbackManager en config["callbacks"]."""
from unittest.mock import MagicMock

from src.core.engine import create_observable_config


def test_create_observable_config_with_callback_manager() -> None:
    """Bug 6: config["callbacks"] puede ser un CallbackManager, no una lista."""
    # Simular un AsyncCallbackManager (no iterable)
    fake_manager = MagicMock()
    fake_manager.__iter__ = MagicMock(side_effect=TypeError("not iterable"))
    fake_manager.handlers = []

    config = {"callbacks": fake_manager}
    result = create_observable_config("chat_response", config)

    # Debe normalizar a lista y agregar el handler
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1
    assert result["callbacks"][0].__class__.__name__ == "LLMObservabilityHandler"


def test_create_observable_config_with_none_callbacks() -> None:
    """config["callbacks"] puede ser None."""
    config: dict = {"callbacks": None}
    result = create_observable_config("chat_response", config)
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1


def test_create_observable_config_with_list_callbacks() -> None:
    """Caso normal: callbacks es una lista."""
    config: dict = {"callbacks": []}
    result = create_observable_config("chat_response", config)
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1


def test_create_observable_config_no_config() -> None:
    """Sin config — debe crear uno nuevo."""
    result = create_observable_config("general")
    assert isinstance(result["callbacks"], list)
    assert len(result["callbacks"]) == 1
```

### Step 2: Ejecutar test para verificar que falla

```bash
uv run pytest tests/unit/core/test_observable_config.py -v
```

Esperado: `test_create_observable_config_with_callback_manager` FALLA con `TypeError: 'AsyncCallbackManager' object is not iterable`.

### Step 3: Aplicar el fix en `src/core/engine.py:24-33`

Reemplazar las líneas 24-33 con el código normalizado descrito arriba.

### Step 4: Ejecutar tests para verificar que pasan

```bash
uv run pytest tests/unit/core/test_observable_config.py -v
```

Esperado: 4/4 PASS.

### Step 5: `make verify`

```bash
make verify
```

Esperado: Los archivos modificados pasan ruff + mypy. Los errores pre-existentes de otros archivos no son bloqueantes.

### Step 6: Commit

```bash
git add src/core/engine.py tests/unit/core/test_observable_config.py
git commit -m "fix(observability): handle AsyncCallbackManager in create_observable_config

Bug 6: LangChain passes AsyncCallbackManager (not a list) in
config['callbacks'] when running LCEL chains internally. Normalize
callbacks to list before iterating to prevent TypeError."
```

---

## Fase 2: Fix Bug 8 — Prompt template con variables sin escapar

### Objetivo
Que el prompt de `_generate_transversal_edges` no interprete las llaves del JSON de ejemplo como variables de template.

### Justificación
El consolidation worker no puede generar aristas transversales porque el prompt falla al parsear. Es un bug menor (warning, no crash) pero degrada la funcionalidad de Graph RAG.

### Cambios Previstos

- **Módulo:** `src/memory/consolidation_worker.py`
  - **Acción:** Modificar
  - **Línea:** 198
  - **Descripción:** Escapar las llaves del JSON de ejemplo en el system prompt: `{\"origen\"` → `{{\"origen\"`, etc.
  - **Consumidores:** Ninguno externo

### Detalle del Fix

**Código actual** (`src/memory/consolidation_worker.py:198`):
```python
'[{"origen": "llave_hecho_1", "destino": "llave_hecho_2", "tipo": "causa", "peso": 0.85, "evidencia": "El usuario indica que..."}]\n'
```

LangChain interpreta `{"origen"` como variable de template `origen"`. El fix es escapar con doble llave: `{{"origen"`.

**Fix:**
```python
'[{{"origen": "llave_hecho_1", "destino": "llave_hecho_2", "tipo": "causa", "peso": 0.85, "evidencia": "El usuario indica que..."}}]\n'
```

### Step 1: Aplicar fix en `src/memory/consolidation_worker.py:198`

Reemplazar la línea 198 escapando las llaves del JSON de ejemplo.

### Step 2: Verificar que el test existente sigue pasando

```bash
uv run pytest tests/unit/memory/test_worker_edges.py -v
```

### Step 3: `make verify` (solo archivos modificados)

```bash
uv run ruff check src/memory/consolidation_worker.py
uv run mypy src/memory/consolidation_worker.py
```

### Step 4: Commit

```bash
git add src/memory/consolidation_worker.py
git commit -m "fix(memory): escape JSON braces in transversal edges prompt template

Bug 8: ChatPromptTemplate interpreted {origen}, {destino}, {tipo},
{peso}, {evidencia} inside JSON example as template variables.
Escaped with double braces."
```

---

## Fase 3: Fix Bug 9 — `SQLiteStore` no tiene `.execute()`

### Objetivo
Que `_check_edges_exist` use la API correcta de `SQLiteStore` para ejecutar queries.

### Justificación
El context retriever no puede verificar si existen aristas para activar Graph RAG. Es un bug menor (degradación suave ya existe) pero impide la expansión de contexto por grafo.

### Cambios Previstos

- **Módulo:** `src/agents/orchestrator/context_retriever.py`
  - **Acción:** Modificar
  - **Líneas:** 75-79
  - **Descripción:** Reemplazar `store.execute()` por `db = await store.get_db()` seguido de `db.execute()`.
  - **Consumidores:** Ninguno externo

### Detalle del Fix

**Código actual** (`src/agents/orchestrator/context_retriever.py:75-79`):
```python
try:
    params = memory_ids + memory_ids
    result = await store.execute(query, params)
    rows = await result.fetchone()
    return rows is not None
```

**Fix:**
```python
try:
    params = memory_ids + memory_ids
    db = await store.get_db()
    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchone()
    return rows is not None
```

### Step 1: Aplicar fix en `src/agents/orchestrator/context_retriever.py:75-79`

### Step 2: Verificar que el test existente sigue pasando

```bash
uv run pytest tests/unit/memory/test_graph_rag_activation.py -v
```

### Step 3: Fix del f-string en logging (línea 81)

La línea 81 usa f-string en logger — ruff T201/G004 podría quejarse:
```python
# Actual:
logger.warning(f"Error verificando aristas en memory_edges: {e}")
# Fix:
logger.warning("Error verificando aristas en memory_edges: %s", e)
```

### Step 4: `make verify` (solo archivos modificados)

```bash
uv run ruff check src/agents/orchestrator/context_retriever.py
uv run mypy src/agents/orchestrator/context_retriever.py
```

### Step 5: Commit

```bash
git add src/agents/orchestrator/context_retriever.py
git commit -m "fix(context): use store.get_db() instead of nonexistent store.execute()

Bug 9: SQLiteStore has no .execute() method. Use get_db() to obtain
the aiosqlite connection, then execute query via async context manager."
```

---

## Fase 4: Fix Bug 7 — Logging diagnóstico para backup GCS 403

### Objetivo
Mejorar el logging cuando el backup a GCS falla por permisos, para facilitar diagnóstico futuro.

### Justificación
El backup falla silenciosamente con un error genérico. El código actual no distingue entre error de auth, error de red, o bucket inexistente. Este NO es un bug de código sino de configuración IAM, pero el logging pobre dificulta el diagnóstico. El fix es solo logging — no se modifica la lógica.

### Cambios Previstos

- **Módulo:** `src/memory/backup.py`
  - **Acción:** Modificar
  - **Líneas:** 72-73
  - **Descripción:** Agregar logging específico para errores 403/401 con instrucciones de diagnóstico.
  - **Consumidores:** Ninguno externo

### Detalle del Fix

**Código actual** (`src/memory/backup.py:72-73`):
```python
except Exception as e:
    logger.error("Backup failed: %s", e)
```

**Fix:**
```python
except Exception as e:
    error_msg = str(e)
    if "403" in error_msg or "401" in error_msg:
        logger.error(
            "Backup auth failed (IAM/scope issue): %s. "
            "Verify service account has 'Storage Object Admin' role "
            "on bucket '%s'.",
            e,
            self.bucket_name,
        )
    else:
        logger.error("Backup failed: %s", e)
```

### Step 1: Aplicar fix en `src/memory/backup.py:72-73`

### Step 2: `make verify` (solo archivos modificados)

```bash
uv run ruff check src/memory/backup.py
uv run mypy src/memory/backup.py
```

### Step 3: Commit

```bash
git add src/memory/backup.py
git commit -m "fix(backup): add diagnostic logging for GCS auth failures

Bug 7: GCS backup fails with 403 but error message doesn't guide
toward the fix. Added specific logging for auth/permission errors
with actionable IAM instructions."
```

---

## Fase 5: Deploy y verificación en producción

### Step 1: Push a develop

```bash
git push origin develop
```

### Step 2: Deploy en VM

```bash
# En la VM:
git pull origin develop && docker-compose build app && docker-compose down && docker-compose up -d
```

### Step 3: Verificar en logs

```bash
docker-compose logs -f --tail 50
```

**Criterios de éxito:**
- [ ] App arranca sin errores
- [ ] Polling conecta y reenvía mensajes (sin "API Local no disponible")
- [ ] EnhancedRouter analiza mensajes sin `AsyncCallbackManager` error
- [ ] `conversational_chat_tool` ejecuta sin error y MAGI responde en Telegram
- [ ] `consolidation_worker` no muestra warning de `{origen}` template variable
- [ ] `_check_edges_exist` no muestra warning de `SQLiteStore.execute`
- [ ] Backup muestra mensaje diagnóstico claro (si sigue el 403 de GCS)

---

## Seguimiento de Tareas

- [ ] Fase 1: Fix Bug 6 — `AsyncCallbackManager` (test + fix + verify)
- [ ] Fase 2: Fix Bug 8 — Prompt template escapado
- [ ] Fase 3: Fix Bug 9 — `store.get_db()` en context_retriever
- [ ] Fase 4: Fix Bug 7 — Logging diagnóstico backup GCS
- [ ] Fase 5: Deploy y verificación en producción

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|

---

## Notas y Riesgos

1. **Bug 6 es el único bloqueante.** Los bugs 7, 8 y 9 ya tienen degradación suave (warnings, no crashes). Pero todos deben corregirse para funcionalidad completa.
2. **Bug 7 requiere acción de infraestructura** adicional al cambio de código: configurar el service account de la VM con el rol `Storage Object Admin` en el bucket `aegen-backups-jjhonn`. Esto está fuera del scope del código.
3. **Orden de ejecución importa:** Bug 6 primero (desbloquea todo), luego 8/9 (pueden ir en paralelo), luego 7 (solo logging).
