# AEGEN - Plan A.2 Reformulado: Vigilante de Conocimiento

### Paso 1: Refactorizar `GlobalKnowledgeLoader` (requisito previo)

**Archivo:** `src/memory/global_knowledge_loader.py`

**Objetivo:** Extraer la lógica de procesamiento de un solo archivo a un método reutilizable.

**Cambios:**
- Extraer un nuevo método público `async ingest_file(self, file_path: Path) -> int`
  - Contiene la lógica de las líneas 110-147 (leer contenido, llamar `store_context`)
  - Retorna el número de chunks nuevos
- Simplificar `sync_knowledge()` para que itere y llame a `ingest_file()` internamente
- Esto **no cambia el comportamiento** actual, solo reorganiza el código

### Paso 2: Implementar método de eliminación por archivo

**Archivo:** `src/memory/sqlite_store.py` (o `src/memory/repositories/memory_repo.py`)

**Objetivo:** Permitir borrar todos los chunks asociados a un archivo específico.

**Cambios:**
- Nuevo método `async delete_memories_by_filename(self, filename: str, namespace: str = "global") -> int`
  - SQL: `UPDATE memories SET is_active = 0 WHERE namespace = ? AND metadata LIKE '%"filename": "..."'`
  - Usa soft-delete (coherente con el patrón existente `soft_delete_memories`)
- Exponer a través de `VectorMemoryManager` como `async delete_file_knowledge(filename) -> int`

### Paso 3: Implementar `KnowledgeWatcher`

**Archivo nuevo:** `src/memory/knowledge_watcher.py` (~100-120 LOC)

**Clase `KnowledgeWatcher`:**

```python
__init__(self, loader: GlobalKnowledgeLoader, interval: int = 30)
```

- Recibe el `GlobalKnowledgeLoader` existente por inyección de dependencia
- Almacena un diccionario interno `_file_snapshots: dict[str, float]` con `{filename: mtime}` para tracking de estado
- Usa `interval` configurable (default 30 segundos)

**Método `async start(self)`:**
- Toma un snapshot inicial de los archivos (nombre + mtime)
- Lanza `self._watch_task = asyncio.create_task(self._poll_loop())`

**Método `async _poll_loop(self)`:**
- Loop infinito con `await asyncio.sleep(self._interval)`
- Escanea `storage/knowledge/` y compara mtimes contra `_file_snapshots`
- Detecta 3 tipos de evento:
  - **Archivo nuevo** (no estaba en snapshots): llama `loader.ingest_file(path)`
  - **Archivo modificado** (mtime diferente): llama `delete_file_knowledge(filename)` + `loader.ingest_file(path)`
  - **Archivo eliminado** (estaba en snapshots, ya no existe): llama `delete_file_knowledge(filename)`
- Actualiza `_file_snapshots` después de procesar
- Aplica `loader._should_process_file()` como filtro

**Método `async stop(self)`:**
- Cancela `self._watch_task` y espera con `try/except asyncio.CancelledError`

### Paso 4: Integrar en `src/main.py` (lifespan)

**Archivo:** `src/main.py`

**Cambios en `lifespan()`:**
- Después del bootstrap (línea 73), crear e iniciar el watcher:
  ```python
  from src.memory.knowledge_watcher import KnowledgeWatcher
  watcher = KnowledgeWatcher(global_knowledge_loader)
  await watcher.start()
  ```
- Antes de `shutdown_global_resources()` (línea 80), detenerlo:
  ```python
  await watcher.stop()
  ```

### Paso 5: Tests y Verificación

- Test unitario para `KnowledgeWatcher`: simular archivo nuevo, modificado, eliminado
- Test de `ingest_file` aislado
- Ejecutar `make verify` (lint + tests + architecture check)
