# 📋 Plan de Implementación: Migración SQLite + sqlite-vec

## Objetivo
Migrar el sistema de memoria de AEGEN de **Google File API** a **SQLite + sqlite-vec + FTS5**, manteniendo Redis para sesiones activas.

---

## 🎯 Fases del Plan

### **FASE 0: Preparación (1-2 horas)**

| Tarea | Descripción | Verificación |
|-------|-------------|--------------|
| 0.1 | Crear branch `feature/sqlite-memory` | `git branch -a \| grep sqlite` |
| 0.2 | Añadir dependencias a `pyproject.toml`: `aiosqlite`, `sqlite-vec` | `pip install -e .` sin errores |
| 0.3 | Crear directorio `data/` para SQLite en raíz | `ls data/` existe |
| 0.4 | Añadir `data/*.db` a `.gitignore` | `grep "data/" .gitignore` |

---

### **FASE 1: Infraestructura SQLite (3-4 horas)**

| Tarea | Archivo | Descripción |
|-------|---------|-------------|
| 1.1 | `src/memory/sqlite_store.py` | **CREAR** - Clase `SQLiteStore` con conexión async |
| 1.2 | `src/memory/schema.sql` | **CREAR** - Esquema DDL (tables: memories, embeddings, sessions) |
| 1.3 | `src/memory/sqlite_store.py` | Método `init_db()` que ejecuta schema.sql |
| 1.4 | `src/core/dependencies.py` | Añadir `sqlite_connection` singleton |
| 1.5 | `src/core/config/base.py` | Añadir `SQLITE_DB_PATH: str = "data/aegen_memory.db"` |

**Esquema propuesto (`schema.sql`):**
```sql
-- Tabla principal de memorias (texto + metadatos)
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    namespace TEXT DEFAULT 'user',  -- 'global' | 'user_{id}'
    content TEXT NOT NULL,
    content_hash TEXT UNIQUE,       -- SHA-256 para deduplicación
    memory_type TEXT,               -- 'fact', 'preference', 'conversation'
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice FTS5 para búsqueda por keywords
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    content='memories',
    content_rowid='id'
);

-- Triggers para mantener FTS sincronizado
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Tabla vectorial (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
    embedding FLOAT[768]  -- Dimensión de text-embedding-004
);

-- Mapeo vector -> memory
CREATE TABLE IF NOT EXISTS vector_memory_map (
    vector_rowid INTEGER PRIMARY KEY,
    memory_id INTEGER REFERENCES memories(id) ON DELETE CASCADE
);

-- Cache de embeddings
CREATE TABLE IF NOT EXISTS embedding_cache (
    content_hash TEXT PRIMARY KEY,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Verificación Fase 1:**
```bash
python -c "import aiosqlite; import sqlite_vec; print('OK')"
python -c "from src.memory.sqlite_store import SQLiteStore; print('OK')"
```

---

### **FASE 2: Pipeline de Ingestión (4-5 horas)**

| Tarea | Archivo | Descripción |
|-------|---------|-------------|
| 2.1 | `src/memory/chunker.py` | **CREAR** - Chunker recursivo (400 tokens, 80 overlap) |
| 2.2 | `src/memory/embeddings.py` | **CREAR** - Wrapper para Google `text-embedding-004` API |
| 2.3 | `src/memory/deduplicator.py` | **CREAR** - Hash SHA-256 + verificación en cache |
| 2.4 | `src/memory/ingestion_pipeline.py` | **CREAR** - Orquestador: chunk → dedupe → embed → store |
| 2.5 | `src/memory/sqlite_store.py` | Métodos `insert_memory()`, `insert_vector()` |

**Chunker (`chunker.py`) - Pseudocódigo:**
```python
class RecursiveChunker:
    def __init__(self, chunk_size=400, overlap=80):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        # Dividir por párrafos primero, luego por oraciones si excede
        # Retornar lista de {"content": str, "metadata": dict}
```

**Embeddings (`embeddings.py`):**
```python
class EmbeddingService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Batch call a Google text-embedding-004
        # Usar cache local antes de llamar API
```

**Verificación Fase 2:**
```bash
pytest tests/unit/memory/test_chunker.py -v
pytest tests/unit/memory/test_embeddings.py -v
```

---

### **FASE 3: Búsqueda Híbrida (3-4 horas)**

| Tarea | Archivo | Descripción |
|-------|---------|-------------|
| 3.1 | `src/memory/vector_search.py` | **CREAR** - KNN search con sqlite-vec |
| 3.2 | `src/memory/keyword_search.py` | **CREAR** - FTS5 search |
| 3.3 | `src/memory/hybrid_search.py` | **CREAR** - RRF ranking (0.7 vector + 0.3 keyword) |
| 3.4 | `src/memory/vector_memory_manager.py` | **REESCRIBIR** - Usar hybrid_search |

**RRF Ranking (`hybrid_search.py`):**
```python
def reciprocal_rank_fusion(
    vector_results: list[tuple[int, float]],  # (doc_id, score)
    keyword_results: list[tuple[int, float]],
    k: int = 60,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> list[int]:
    # Calcular RRF score para cada documento
    # Retornar doc_ids ordenados por score combinado
```

**Verificación Fase 3:**
```bash
pytest tests/integration/test_hybrid_search.py -v
```

---

### **FASE 4: Hooks de Sesión (2-3 horas)**

| Tarea | Archivo | Descripción |
|-------|---------|-------------|
| 4.1 | `src/memory/session_processor.py` | **CREAR** - Procesa buffer al cerrar sesión |
| 4.2 | `src/core/session_manager.py` | **MODIFICAR** - Añadir hook `on_session_end()` |
| 4.3 | `src/memory/long_term_memory.py` | **MODIFICAR** - Reemplazar `file_search_tool` → `ingestion_pipeline` |
| 4.4 | `src/memory/consolidation_worker.py` | **MODIFICAR** - Usar SQLite en lugar de Google Cloud |

**Flujo del Hook:**
```
Sesión Activa (Redis)
    ↓ [Timeout 30min o cierre explícito]
SessionProcessor.process(chat_id)
    ↓
1. Extraer buffer de Redis
2. LLM genera resumen/hechos
3. Chunker divide el contenido
4. Deduplicator filtra repetidos
5. EmbeddingService genera vectores
6. SQLiteStore persiste todo
7. Limpiar buffer Redis
```

**Verificación Fase 4:**
```bash
# Test end-to-end simulando cierre de sesión
pytest tests/integration/test_session_hook.py -v
```

---

### **FASE 5: Limpieza de Código Legacy (2 horas)**

| Tarea | Archivo | Acción |
|-------|---------|--------|
| 5.1 | `src/tools/google_file_search.py` | **ELIMINAR** |
| 5.2 | `src/memory/cloud_gateway.py` | **ELIMINAR** |
| 5.3 | `src/memory/redis_fallback.py` | **ELIMINAR** |
| 5.4 | `src/memory/maintenance_job.py` | **ELIMINAR** |
| 5.5 | `src/memory/hybrid_coordinator.py` | **ELIMINAR** |
| 5.6 | `src/memory/consistency_manager.py` | **ELIMINAR** |
| 5.7 | `scripts/check_cloud_files.py` | **ELIMINAR** |
| 5.8 | `src/memory/knowledge_base.py` | **MODIFICAR** - Remover imports de cloud_gateway |
| 5.9 | `src/core/profile_manager.py` | **MODIFICAR** - Usar SQLite para persistencia de perfiles |
| 5.10 | Todos los archivos | `grep -r "file_search_tool\|cloud_gateway" src/` debe estar vacío |

**Verificación Fase 5:**
```bash
# No debe haber referencias a Google File API
grep -r "google_file_search\|cloud_gateway\|file_search_tool" src/
# Debe retornar vacío
```

---

### **FASE 6: Tests y Validación (3-4 horas)**

| Tarea | Descripción |
|-------|-------------|
| 6.1 | Crear `tests/unit/memory/test_sqlite_store.py` |
| 6.2 | Crear `tests/unit/memory/test_chunker.py` |
| 6.3 | Crear `tests/unit/memory/test_hybrid_search.py` |
| 6.4 | Crear `tests/integration/test_memory_e2e.py` |
| 6.5 | Ejecutar `make verify` completo |
| 6.6 | Test manual: enviar mensajes por Telegram, cerrar sesión, verificar SQLite |

**Test E2E (`test_memory_e2e.py`):**
```python
async def test_full_memory_cycle():
    # 1. Simular 5 mensajes de usuario
    # 2. Triggear consolidación
    # 3. Buscar con query semántica
    # 4. Verificar que encuentra el contenido
    # 5. Buscar con keyword exacto
    # 6. Verificar resultados combinados
```

---

### **FASE 7: Respaldo Cloud (Opcional, post-MVP)**

| Tarea | Descripción |
|-------|-------------|
| 7.1 | Crear `scripts/backup_to_gcs.py` |
| 7.2 | Configurar cron job diario para `sqlite3 backup` |
| 7.3 | Subir `.db` comprimido a Google Cloud Storage |

---

## 📁 Estructura Final de `src/memory/`

```
src/memory/
├── __init__.py
├── schema.sql              # DDL de SQLite
├── sqlite_store.py         # Conexión y operaciones SQLite
├── chunker.py              # Chunking recursivo
├── deduplicator.py         # Hash + cache
├── embeddings.py           # Google text-embedding-004
├── ingestion_pipeline.py   # Orquestador de ingestión
├── vector_search.py        # KNN con sqlite-vec
├── keyword_search.py       # FTS5
├── hybrid_search.py        # RRF ranking
├── vector_memory_manager.py # API pública (reescrito)
├── session_processor.py    # Hook de fin de sesión
├── long_term_memory.py     # Modificado
├── consolidation_worker.py # Modificado
├── knowledge_base.py       # Modificado
├── redis_buffer.py         # Sin cambios
├── fact_extractor.py       # Sin cambios
├── memory_factory.py       # Modificado
└── global_knowledge_loader.py # Modificado
```

---

## ⏱️ Estimación Total

| Fase | Horas |
|------|-------|
| 0. Preparación | 1-2 |
| 1. Infraestructura SQLite | 3-4 |
| 2. Pipeline de Ingestión | 4-5 |
| 3. Búsqueda Híbrida | 3-4 |
| 4. Hooks de Sesión | 2-3 |
| 5. Limpieza Legacy | 2 |
| 6. Tests y Validación | 3-4 |
| **TOTAL** | **18-24 horas** |

---

## ❓ Preguntas para Ti Antes de Proceder

1. **¿Confirmas la dimensión del embedding?** Google `text-embedding-004` usa 768 dimensiones. ¿Esto está alineado con tu configuración actual?
2. **¿Quieres que `data/` esté en la raíz del proyecto o dentro de `src/`?**
3. **¿El modelo RAG actual (`gemini-2.5-flash-lite`) se usará solo para embeddings o también para otros fines?** Necesito saber si debo mantener alguna referencia.
4. **¿Prefieres que empecemos por la Fase 1 (infraestructura) o quieres que primero escriba los tests (TDD)?**
