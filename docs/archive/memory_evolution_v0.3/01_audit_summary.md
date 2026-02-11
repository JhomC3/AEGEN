# Resumen de Sesión: Migración de Arquitectura de Memoria AEGEN

**📍 Ubicación del Proyecto:** `/Users/jhomc/Proyectos/AEGEN/`

---

## ✅ Lo Que Hicimos

### 1. Análisis Profundo de OpenClaw
Investigamos la arquitectura de memoria de [OpenClaw](https://github.com/openclaw/openclaw) como referencia. Documentamos todo en:
`docs/research/analisis_memoria_openclaw.md`

**Características clave de OpenClaw que vamos a implementar:**
- **SQLite + sqlite-vec:** Base vectorial local (<10ms latencia).
- **FTS5:** Motor de búsqueda por palabras clave.
- **Búsqueda Híbrida:** 70% vector + 30% keyword.
- **Chunking Recursivo:** 400 tokens con 80 de overlap.
- **Cache de Embeddings:** Evita llamadas API duplicadas.
- **Hooks de Sesión:** Procesa y guarda al cerrar sesión.

### 2. Auditoría Completa del Código Actual de AEGEN
Exploramos todo el código de memoria existente. Estado actual:
- **Redis:** Completamente integrado (cache, sesiones, buffers).
- **Google File API:** Usado para RAG (latencia 0.5s-2s, problemático).
- **ChromaDB:** Eliminado, quedan solo stubs.
- **SQLite:** NO instalado actualmente.

### 3. Inventario de Archivos (Acciones Requeridas)

#### 🔴 ELIMINAR (7 archivos):
- `src/memory/redis_fallback.py`
- `src/memory/cloud_gateway.py`
- `src/memory/maintenance_job.py`
- `src/memory/hybrid_coordinator.py`
- `src/memory/consistency_manager.py`
- `src/tools/google_file_search.py`
- `scripts/check_cloud_files.py`

#### 🟠 REESCRIBIR (3 archivos):
- `src/memory/vector_memory_manager.py`  → Implementar con `sqlite-vec`.
- `src/core/session_manager.py`          → SQLite sessions table.
- `tests/integration/test_redis_memory.py` → Tests para SQLite.

#### 🟡 MODIFICAR (12 archivos):
- `src/memory/redis_buffer.py`
- `src/memory/long_term_memory.py`
- `src/memory/knowledge_base.py`
- `src/memory/consolidation_worker.py`
- `src/memory/global_knowledge_loader.py`
- `src/memory/memory_factory.py`
- `src/core/dependencies.py`
- `src/core/profile_manager.py`
- `src/api/routers/webhooks.py`
- `src/main.py`
- `src/core/config/base.py`
- `scripts/reset_user_memory.py`

#### 🟢 CONSERVAR (4 archivos):
- `src/memory/__init__.py`
- `src/memory/fact_extractor.py`
- `tests/unit/core/bus/test_in_memory.py`
- `RAG_MODEL` config (para embeddings).

---

## 🎯 Decisiones de Arquitectura Tomadas

| Aspecto | Decisión |
|---------|----------|
| **Memoria Activa (Sesión)** | Mantener Redis (escalabilidad multi-usuario) |
| **Memoria Largo Plazo** | SQLite + sqlite-vec (local en MV) |
| **Búsqueda Texto** | FTS5 (integrado en SQLite) |
| **Embeddings** | API Google `text-embedding-004` (no File Search) |
| **Chunking** | 400 tokens / 80 overlap |
| **Búsqueda** | Híbrida (0.7 vector + 0.3 keyword) |
| **Privacidad** | Namespaces: `global` vs `user_{id}` |
| **Respaldo** | SQLite → Google Cloud Storage (1x día) |

---

## ⏭️ Lo Que Falta Hacer
Estábamos a punto de crear el plan de implementación detallado cuando se solicitó este resumen. El plan debe seguir el formato de `/Users/jhomc/Proyectos/AEGEN/` con tareas específicas y verificables.

**Fases Propuestas:**
1. **Infraestructura:** Instalar dependencias, crear esquema SQLite.
2. **Ingestión:** Chunker, Deduplicador, llamada a Embeddings API.
3. **Búsqueda:** Híbrida (FTS5 + sqlite-vec), Ranking RRF.
4. **Hooks:** Procesar sesión al cerrar, sincronizar con LLM.
5. **Limpieza:** Eliminar código legacy.
6. **Verificación:** Tests, validación end-to-end.

---

## 📁 Archivos Clave de Referencia
`/Users/jhomc/Proyectos/AEGEN/`
├── `docs/research/analisis_memoria_openclaw.md`    # Arquitectura OpenClaw documentada
├── `src/memory/`                          # Módulo a refactorizar
├── `src/tools/google_file_search.py`      # A ELIMINAR
├── `src/core/config/base.py`              # Configuración actual
└── `pyproject.toml`                       # Dependencias

---

## 🔧 Dependencias a Gestionar
**AÑADIR:**
- `sqlite-vec` (extensión vectorial)
- `aiosqlite` (async SQLite)

**EVALUAR ELIMINAR:**
- `redis[hiredis]` → Mantener por ahora para sesiones activas
- Referencias a ChromaDB en configs

---

## 💬 Prompt para Continuar (Contexto de Sesión)
> Estoy trabajando en AEGEN, un sistema de agentes conversacionales en Python ubicado en /Users/jhomc/Proyectos/AEGEN/
>
> CONTEXTO PREVIO:
> 1. Analizamos OpenClaw como referencia de arquitectura de memoria
> 2. Documentamos todo en docs/research/analisis_memoria_openclaw.md
> 3. Auditamos el código actual: Redis integrado, Google File API problemático, ChromaDB eliminado
> 4. Identificamos 7 archivos a ELIMINAR, 3 a REESCRIBIR, 12 a MODIFICAR
>
> DECISIONES TOMADAS:
> - Migrar de Google File API → SQLite + sqlite-vec + FTS5
> - Mantener Redis solo para sesiones activas
> - Usar API de embeddings de Google (text-embedding-004)
> - Implementar búsqueda híbrida (vector + keyword)
> - Chunking: 400 tokens, 80 overlap
> - Namespaces: global vs user_{id} para privacidad
