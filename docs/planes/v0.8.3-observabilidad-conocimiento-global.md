# Plan v0.8.3: Observabilidad y Calidad del Conocimiento Global

> **Para Agentes:** SKILL REQUERIDO: Usar `executing-plans` para implementar este plan tarea por tarea.

**Meta:** Resolver el fallo de ingesta de conocimiento global (reporte `v0.7.2-analisis-fallo-ingesta-global.md`) e implementar observabilidad completa del ciclo de vida del conocimiento: desde la ingesta hasta el uso por los especialistas. Garantizar que la información global se recupere adecuadamente y que su uso sea rastreable.

**Arquitectura:** Se aplican 5 capas defensivas: (1) Fix del filtro de seguridad con lista blanca CORE_ y logging explícito de decisiones, (2) Auditor de conocimiento para inventario y verificación bajo demanda, (3) Trazas RAG estructuradas en logs JSON para cada búsqueda, (4) Endpoint REST de diagnóstico para consultar estado del conocimiento, (5) Transparencia enriquecida en especialistas CBT/Chat sobre qué contexto se inyectó.

**Stack Afectado:** Python 3.12, aiosqlite, FastAPI, Pydantic v2, SQLite, sqlite-vec.

**ADR Relacionado:** ADR-0025 (a crear en este plan).

**Reporte Base:** `docs/reportes/v0.7.2-analisis-fallo-ingesta-global.md`

---

## Diagnóstico: Mapa de Problemas

| ID | Problema | Causa Raíz | Archivos Afectados | Severidad |
|----|----------|------------|---------------------|-----------|
| P1 | Ingesta silenciosamente falla | Regex `\d{5,}` en `_should_process_file` descarta archivos CORE_ con ISBN sin distinguir origen. No hay logging de por qué se descarta. | `src/memory/global_knowledge_loader.py:59-82` | **Crítica** |
| P2 | Sin registro de qué está ingresado | No existe inventario de documentos globales. Solo se puede inferir consultando `memories WHERE namespace='global'` directamente. | `src/memory/` (falta módulo de auditoría) | **Alta** |
| P3 | Sin trazabilidad RAG | Los logs dicen `"3 global + 2 user fragments"` pero no qué fragmentos, de qué documento, con qué score, ni qué query se usó. | `src/memory/vector_memory_manager.py:67-82` | **Alta** |
| P4 | Sin verificación de recuperabilidad | No hay forma de saber si un documento ingresado es realmente recuperable via búsqueda semántica. | No existe | **Media** |
| P5 | Sin visibilidad en especialistas | No se registra qué documentos se usaron para construir el contexto de cada respuesta. | `src/agents/specialists/cbt/cbt_tool.py:70-74`, `chat_tool.py` | **Media** |

---

## Tarea 0: ADR-0025 - Decisión Arquitectónica

**Archivos:**
- Crear: `adr/ADR-0025-observabilidad-conocimiento-global.md`

### Paso 1: Crear el ADR

```markdown
# ADR-0025: Observabilidad y Calidad del Conocimiento Global

- **Estado:** Aceptado
- **Decisores:** Jhonn Muñoz C., AI Assistant (Opencode)
- **Fecha:** 2026-02-16
- **Contexto:** Post-mortem del fallo de ingesta v0.7.2

## Contexto

El reporte `v0.7.2-analisis-fallo-ingesta-global.md` documentó un fallo en el que
el filtro de seguridad de `GlobalKnowledgeLoader._should_process_file()` descartaba
silenciosamente archivos legítimos del sistema (prefijo `CORE_`) que contenían
ISBNs en el nombre, interpretándolos como IDs de usuario de Telegram.

Más allá del bug, el incidente expuso la ausencia de observabilidad en el pipeline
de conocimiento global: fallos silenciosos en ingesta, sin registro de qué está
ingresado, sin trazas RAG, y sin verificación de recuperabilidad.

## Decisión

1. **Lista Blanca CORE_**: Los archivos con prefijo `core_` (case-insensitive) omiten
   la verificación de IDs numéricos. El filtro retorna una tupla `(bool, str)` con
   la razón de aceptación/rechazo para logging explícito.

2. **Auditor de Conocimiento**: Nuevo módulo `knowledge_auditor.py` que consulta la tabla
   `memories` para obtener inventario y estadísticas por documento. Verificación de
   recuperabilidad semántica solo bajo demanda (via endpoint REST).

3. **Trazas RAG en Logs Estructurados**: Cada búsqueda en `VectorMemoryManager.retrieve_context()`
   genera un log JSON enriquecido con: query, fragmentos recuperados, scores, fuentes, y
   latencia. Consultable con `jq` sobre los logs JSON del sistema.

4. **Endpoint de Diagnóstico**: `GET /system/diagnostics/knowledge` retorna el estado completo
   del conocimiento global. Registrado bajo el prefix `/system` existente.

5. **Sin Atribución en Prompt**: Los fragmentos RAG se inyectan como texto plano al LLM,
   sin marcadores de fuente. La trazabilidad se gestiona exclusivamente via logs.

## Consecuencias

### Positivas
- Eliminación de fallos silenciosos en ingesta.
- Visibilidad completa del ciclo de vida del conocimiento (ingesta → almacenamiento → recuperación → uso).
- Capacidad de diagnosticar problemas de calidad RAG sin acceso a la DB.
- Costo cero en almacenamiento adicional (logs, no tablas nuevas).

### Negativas
- El endpoint de diagnóstico con verificación genera N+1 embeddings bajo demanda.
- Volumen de logs incrementado (~200 bytes/búsqueda RAG adicional).
```

### Paso 2: Commit

```bash
git add adr/ADR-0025-observabilidad-conocimiento-global.md
git commit -m "docs(adr): ADR-0025 observabilidad y calidad de conocimiento global"
```

---

## Tarea 1: Fix del Filtro de Seguridad + Logging Explícito (Problema P1)

> Resuelve la causa raíz: archivos CORE_ descartados silenciosamente por contener ISBNs.

**Archivos:**
- Modificar: `src/memory/global_knowledge_loader.py:59-82, 131-161`
- Modificar: `src/memory/knowledge_watcher.py:71`
- Test: `tests/unit/memory/test_global_knowledge_loader.py` (crear)

### Paso 1: Escribir los tests que fallan

```python
# tests/unit/memory/test_global_knowledge_loader.py
from pathlib import Path

import pytest

from src.memory.global_knowledge_loader import GlobalKnowledgeLoader


class TestShouldProcessFile:
    """Verifica el filtro de seguridad de archivos globales."""

    def setup_method(self):
        self.loader = GlobalKnowledgeLoader.__new__(GlobalKnowledgeLoader)
        self.loader.knowledge_path = Path("/tmp/test_knowledge")

    def test_core_prefix_bypasses_numeric_filter(self):
        """CORE_ con ISBN debe ser aceptado (causa raíz del bug v0.7.2)."""
        path = Path("CORE_Unified_Protocol_9780190685973.pdf")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True
        assert reason == "aceptado"

    def test_core_prefix_case_insensitive(self):
        """core_ en minúsculas también debe funcionar."""
        path = Path("core_guia_esencial.pdf")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_user_id_file_rejected(self):
        """Archivo con ID de usuario largo (no CORE_) debe ser rechazado."""
        path = Path("123456789_chat_export.txt")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is False
        assert "id_usuario" in reason

    def test_legacy_keywords_rejected(self):
        """Archivos con keywords legacy deben ser rechazados."""
        for name in ["buffer_export.txt", "user_summary.md", "vault_data.txt", "profile_backup.pdf"]:
            path = Path(name)
            should_process, reason = self.loader._should_process_file(path)
            assert should_process is False, f"{name} debería ser rechazado"
            assert "keyword" in reason

    def test_unsupported_extension_rejected(self):
        """Extensiones no soportadas deben ser rechazadas."""
        path = Path("notes.docx")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is False
        assert "extension" in reason

    def test_valid_text_file_accepted(self):
        """Archivo de texto normal debe ser aceptado."""
        path = Path("guia_practica.txt")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_valid_markdown_accepted(self):
        """Archivo markdown debe ser aceptado."""
        path = Path("reference_guide.md")
        should_process, reason = self.loader._should_process_file(path)
        assert should_process is True

    def test_returns_tuple(self):
        """Siempre retorna una tupla (bool, str)."""
        path = Path("test.pdf")
        result = self.loader._should_process_file(path)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
```

### Paso 2: Ejecutar test para verificar que falla

```bash
pytest tests/unit/memory/test_global_knowledge_loader.py -v
```
Esperado: FAIL — el método actual retorna `bool`, no `tuple`.

### Paso 3: Modificar `_should_process_file()` en `global_knowledge_loader.py`

Reemplazar `_should_process_file` (líneas 59-82) por:

```python
def _should_process_file(self, file_path: Path) -> tuple[bool, str]:
    """
    Determina si un archivo debe ser procesado como conocimiento global.
    Retorna (should_process, reason) para trazabilidad de decisiones.
    """
    import re

    name = file_path.name.lower()
    ext = file_path.suffix.lower()

    # 1. Solo permitir PDF, Markdown y Texto
    if ext not in (".pdf", ".md", ".txt"):
        return False, f"extension_no_permitida: {ext}"

    # 2. Lista blanca: archivos CORE_ omiten verificación numérica
    is_core = name.startswith("core_")

    # 3. Ignorar archivos con IDs de usuario (solo para no-CORE)
    if not is_core and re.search(r"\d{5,}", name):
        return False, "posible_id_usuario_detectado"

    # 4. Ignorar palabras clave de archivos personales legacy
    ignore_keywords = ("buffer", "summary", "vault", "profile")
    for kw in ignore_keywords:
        if kw in name:
            return False, f"keyword_personal_legacy: {kw}"

    return True, "aceptado"
```

### Paso 4: Actualizar `sync_knowledge()` con logging explícito

Reemplazar el bloque de iteración en `sync_knowledge()` (líneas 147-157) por:

```python
for file_path in self.knowledge_path.glob("*"):
    if file_path.is_dir() or file_path.name.startswith("."):
        continue

    should_process, reason = self._should_process_file(file_path)
    if not should_process:
        logger.info(
            f"[INGESTA] Archivo descartado: {file_path.name} | "
            f"Razón: {reason}"
        )
        skipped_count += 1
        continue

    await self.ingest_file(file_path)
    processed_count += 1
```

### Paso 5: Actualizar `knowledge_watcher.py` para nueva firma

En `src/memory/knowledge_watcher.py:71`, reemplazar:

```python
# Antes (línea 71):
if self.loader._should_process_file(file_path):
# Después:
should_process, _ = self.loader._should_process_file(file_path)
if should_process:
```

### Paso 6: Ejecutar tests

```bash
pytest tests/unit/memory/test_global_knowledge_loader.py tests/memory/test_knowledge_watcher.py -v
```
Esperado: PASS (todos)

### Paso 7: Commit

```bash
git add src/memory/global_knowledge_loader.py src/memory/knowledge_watcher.py \
  tests/unit/memory/test_global_knowledge_loader.py
git commit -m "fix(memory): lista blanca CORE_ y logging explícito en filtro de ingesta (P1)"
```

---

## Tarea 2: Auditor de Conocimiento (Problemas P2 + P4)

> Módulo de auditoría para inventario y verificación bajo demanda del conocimiento global.

**Archivos:**
- Crear: `src/memory/knowledge_auditor.py`
- Test: `tests/unit/memory/test_knowledge_auditor.py`

### Paso 1: Escribir los tests que fallan

```python
# tests/unit/memory/test_knowledge_auditor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.knowledge_auditor import KnowledgeAuditor


class TestKnowledgeAuditor:
    """Verifica el auditor de conocimiento global."""

    @pytest.mark.asyncio
    async def test_get_knowledge_inventory_returns_list(self):
        """El inventario debe retornar una lista de documentos."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_store = MagicMock()
        mock_db = AsyncMock()
        mock_store.get_db = AsyncMock(return_value=mock_db)
        auditor._store = mock_store

        # Simular resultado de query agrupada
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[
            {"filename": "CORE_Test.pdf", "chunk_count": 50, "last_sync": "2026-02-16"},
        ])
        mock_db.execute = AsyncMock(return_value=mock_cursor)

        result = await auditor.get_knowledge_inventory()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["filename"] == "CORE_Test.pdf"
        assert result[0]["chunk_count"] == 50

    @pytest.mark.asyncio
    async def test_get_global_stats_structure(self):
        """Las estadísticas deben tener la estructura correcta."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_store = MagicMock()
        mock_db = AsyncMock()
        mock_store.get_db = AsyncMock(return_value=mock_db)
        auditor._store = mock_store

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={
            "total_documents": 2, "total_chunks": 847,
            "last_sync": "2026-02-16T10:30:00",
        })
        mock_db.execute = AsyncMock(return_value=mock_cursor)

        result = await auditor.get_global_stats()
        assert "total_documents" in result
        assert "total_chunks" in result
        assert "last_sync" in result

    @pytest.mark.asyncio
    async def test_verify_document_retrievable(self):
        """La verificación debe hacer una búsqueda y confirmar resultados."""
        auditor = KnowledgeAuditor.__new__(KnowledgeAuditor)
        mock_manager = MagicMock()
        mock_manager.retrieve_context = AsyncMock(return_value=[
            {"id": 1, "content": "test", "metadata": {"filename": "CORE_Test.pdf"}},
        ])
        auditor._manager = mock_manager

        result = await auditor.verify_document_retrievable(
            "CORE_Test.pdf", "protocolo unificado"
        )
        assert result["is_retrievable"] is True
        assert result["filename"] == "CORE_Test.pdf"
```

### Paso 2: Ejecutar test para verificar que falla

```bash
pytest tests/unit/memory/test_knowledge_auditor.py -v
```
Esperado: FAIL (`ModuleNotFoundError: No module named 'src.memory.knowledge_auditor'`)

### Paso 3: Implementar `knowledge_auditor.py`

```python
# src/memory/knowledge_auditor.py
"""
Auditor de conocimiento global (ADR-0025).

Provee inventario, estadísticas y verificación bajo demanda
del conocimiento almacenado en el namespace 'global'.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeAuditor:
    """
    Audita el estado del conocimiento global almacenado en SQLite.
    Verificación de recuperabilidad solo bajo demanda.
    """

    def __init__(self):
        self._store = None
        self._manager = None

    @property
    def store(self):
        """Lazy load del SQLiteStore."""
        if self._store is None:
            from src.core.dependencies import get_sqlite_store

            self._store = get_sqlite_store()
        return self._store

    @property
    def manager(self):
        """Lazy load del VectorMemoryManager."""
        if self._manager is None:
            from src.core.dependencies import get_vector_memory_manager

            self._manager = get_vector_memory_manager()
        return self._manager

    async def get_knowledge_inventory(self) -> list[dict[str, Any]]:
        """
        Retorna el inventario de documentos globales con estadísticas.
        """
        db = await self.store.get_db()
        query = """
            SELECT
                json_extract(metadata, '$.filename') as filename,
                COUNT(*) as chunk_count,
                MAX(created_at) as last_sync
            FROM memories
            WHERE namespace = 'global' AND is_active = 1
            GROUP BY json_extract(metadata, '$.filename')
            ORDER BY last_sync DESC
        """
        results = []
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "filename": row["filename"],
                    "chunk_count": row["chunk_count"],
                    "last_sync": row["last_sync"],
                })
        return results

    async def get_global_stats(self) -> dict[str, Any]:
        """Retorna estadísticas globales del conocimiento."""
        db = await self.store.get_db()
        query = """
            SELECT
                COUNT(DISTINCT json_extract(metadata, '$.filename'))
                    as total_documents,
                COUNT(*) as total_chunks,
                MAX(created_at) as last_sync
            FROM memories
            WHERE namespace = 'global' AND is_active = 1
        """
        async with db.execute(query) as cursor:
            row = await cursor.fetchone()
            return {
                "total_documents": row["total_documents"] or 0,
                "total_chunks": row["total_chunks"] or 0,
                "last_sync": row["last_sync"],
            }

    async def verify_document_retrievable(
        self, filename: str, sample_query: str
    ) -> dict[str, Any]:
        """
        Verifica que un documento es recuperable via búsqueda semántica.
        Ejecuta una query de prueba y verifica coincidencia de fuente.
        """
        results = await self.manager.retrieve_context(
            user_id="system",
            query=sample_query,
            limit=5,
            namespace="global",
        )

        found = any(
            r.get("metadata", {}).get("filename") == filename
            for r in results
        )

        logger.info(
            f"[AUDITOR] Verificación de '{filename}': "
            f"{'recuperable' if found else 'NO recuperable'} "
            f"(query: '{sample_query[:50]}...')"
        )

        return {
            "filename": filename,
            "is_retrievable": found,
            "query_used": sample_query[:80],
            "results_returned": len(results),
        }


# Singleton
knowledge_auditor = KnowledgeAuditor()
```

### Paso 4: Ejecutar tests

```bash
pytest tests/unit/memory/test_knowledge_auditor.py -v
```
Esperado: PASS (3/3)

### Paso 5: Commit

```bash
git add src/memory/knowledge_auditor.py tests/unit/memory/test_knowledge_auditor.py
git commit -m "feat(memory): auditor de conocimiento con inventario y verificación bajo demanda (P2/P4)"
```

---

## Tarea 3: Trazas RAG Estructuradas (Problema P3)

> Cada búsqueda RAG genera un log JSON enriquecido consultable con `jq`.

**Archivos:**
- Modificar: `src/memory/vector_memory_manager.py:42-89`

### Paso 1: No requiere test nuevo

La funcionalidad es de logging, no de lógica. Se verifica visualmente y con los tests existentes de `VectorMemoryManager`.

### Paso 2: Modificar `retrieve_context()`

Reemplazar el bloque de transparencia RAG en `vector_memory_manager.py` (líneas 67-82) por:

```python
import time

async def retrieve_context(
    self,
    user_id: str,
    query: str,
    context_type: MemoryType | None = None,
    limit: int = 5,
    namespace: str = "user",
) -> list[dict[str, Any]]:
    """
    Recupera memorias relevantes usando búsqueda híbrida.
    Genera trazas RAG estructuradas para observabilidad.
    """
    start_time = time.monotonic()

    results = await self.hybrid_search.search(
        query=query, limit=limit, chat_id=user_id, namespace=namespace
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Traza RAG estructurada (ADR-0025)
    self._log_rag_trace(
        user_id=user_id,
        namespace=namespace,
        query=query,
        results=results,
        elapsed_ms=elapsed_ms,
    )

    if context_type:
        results = [
            r for r in results if r["memory_type"] == context_type.value
        ]

    return results
```

Y añadir el método privado de logging:

```python
def _log_rag_trace(
    self,
    user_id: str,
    namespace: str,
    query: str,
    results: list[dict[str, Any]],
    elapsed_ms: float,
) -> None:
    """Emite una traza RAG estructurada como log JSON."""
    fragments = [
        {
            "id": r["id"],
            "score": round(r.get("score", 0), 4),
            "source": r.get("metadata", {}).get("filename", "unknown"),
            "type": r.get("memory_type", "unknown"),
            "preview": r["content"][:120],
        }
        for r in results
    ]

    logger.info(
        f"[RAG-TRACE] {namespace}: {len(results)} fragments, "
        f"{elapsed_ms:.0f}ms",
        extra={
            "event": "rag_retrieval",
            "user_id": user_id,
            "namespace": namespace,
            "query_preview": query[:80],
            "results_count": len(results),
            "latency_ms": round(elapsed_ms, 1),
            "fragments": fragments,
        },
    )
```

### Paso 3: Verificar tests existentes

```bash
pytest tests/unit/memory/test_hybrid_search.py -v
```
Esperado: PASS (sin regresión)

### Paso 4: Commit

```bash
git add src/memory/vector_memory_manager.py
git commit -m "feat(memory): trazas RAG estructuradas en VectorMemoryManager (P3)"
```

---

## Tarea 4: Endpoint REST de Diagnóstico (Capa 4)

> Endpoint para consultar el estado completo del conocimiento global.

**Archivos:**
- Crear: `src/api/routers/diagnostics.py`
- Modificar: `src/core/schemas/api.py` (añadir modelos de respuesta)
- Modificar: `src/main.py` (registrar router)
- Test: `tests/unit/api/test_diagnostics.py`

### Paso 1: Añadir modelos Pydantic en `api.py`

En `src/core/schemas/api.py`, añadir al final del archivo:

```python
class KnowledgeDocumentStatus(BaseModel):
    """Estado de un documento de conocimiento global."""

    filename: str
    chunk_count: int
    last_sync: str | None = None
    is_retrievable: bool | None = None


class KnowledgeStatusResponse(BaseModel):
    """Respuesta del endpoint de diagnóstico de conocimiento."""

    status: str
    total_documents: int
    total_chunks: int
    last_sync: str | None = None
    documents: list[KnowledgeDocumentStatus]
```

### Paso 2: Crear `diagnostics.py`

```python
# src/api/routers/diagnostics.py
"""
Endpoints de diagnóstico para observabilidad del conocimiento global (ADR-0025).
"""

import logging

from fastapi import APIRouter, Query

from src.core.schemas.api import KnowledgeDocumentStatus, KnowledgeStatusResponse
from src.memory.knowledge_auditor import knowledge_auditor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/knowledge",
    response_model=KnowledgeStatusResponse,
    tags=["Diagnostics"],
    summary="Estado del conocimiento global ingresado",
)
async def get_knowledge_status(
    verify: bool = Query(
        default=False,
        description="Ejecutar verificación de recuperabilidad semántica",
    ),
    sample_query: str = Query(
        default="protocolo terapéutico técnicas cognitivas",
        description="Query de prueba para verificación de recuperabilidad",
    ),
):
    """
    Retorna el inventario completo del conocimiento global:
    documentos ingresados, cuenta de chunks, última sincronización.
    Opcionalmente verifica la recuperabilidad semántica de cada documento.
    """
    stats = await knowledge_auditor.get_global_stats()
    inventory = await knowledge_auditor.get_knowledge_inventory()

    documents = []
    for doc in inventory:
        doc_status = KnowledgeDocumentStatus(
            filename=doc["filename"],
            chunk_count=doc["chunk_count"],
            last_sync=doc["last_sync"],
        )

        if verify:
            verification = await knowledge_auditor.verify_document_retrievable(
                doc["filename"], sample_query
            )
            doc_status.is_retrievable = verification["is_retrievable"]

        documents.append(doc_status)

    # Estado global: healthy si hay documentos, warning si no
    status = "healthy" if stats["total_documents"] > 0 else "empty"
    if verify:
        all_retrievable = all(
            d.is_retrievable for d in documents if d.is_retrievable is not None
        )
        if not all_retrievable:
            status = "degraded"

    return KnowledgeStatusResponse(
        status=status,
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"],
        last_sync=stats["last_sync"],
        documents=documents,
    )
```

### Paso 3: Registrar router en `main.py`

En `src/main.py`, añadir al import (línea 19):

```python
from src.api.routers import analysis, diagnostics, llm_metrics, status, webhooks
```

Y añadir después de la línea 161:

```python
app.include_router(
    diagnostics.router, prefix="/system/diagnostics", tags=["Diagnostics"]
)
```

### Paso 4: Escribir test

```python
# tests/unit/api/test_diagnostics.py
import pytest
from unittest.mock import AsyncMock, patch


class TestKnowledgeDiagnostics:
    """Verifica el endpoint de diagnóstico de conocimiento."""

    @pytest.mark.asyncio
    async def test_knowledge_status_returns_structure(self, async_client):
        """El endpoint debe retornar la estructura correcta."""
        with patch(
            "src.api.routers.diagnostics.knowledge_auditor"
        ) as mock_auditor:
            mock_auditor.get_global_stats = AsyncMock(return_value={
                "total_documents": 1,
                "total_chunks": 100,
                "last_sync": "2026-02-16T10:00:00",
            })
            mock_auditor.get_knowledge_inventory = AsyncMock(return_value=[
                {
                    "filename": "CORE_Test.pdf",
                    "chunk_count": 100,
                    "last_sync": "2026-02-16T10:00:00",
                }
            ])

            response = await async_client.get(
                "/system/diagnostics/knowledge"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["total_documents"] == 1
            assert len(data["documents"]) == 1

    @pytest.mark.asyncio
    async def test_empty_knowledge_returns_empty_status(self, async_client):
        """Sin documentos, el status debe ser 'empty'."""
        with patch(
            "src.api.routers.diagnostics.knowledge_auditor"
        ) as mock_auditor:
            mock_auditor.get_global_stats = AsyncMock(return_value={
                "total_documents": 0,
                "total_chunks": 0,
                "last_sync": None,
            })
            mock_auditor.get_knowledge_inventory = AsyncMock(return_value=[])

            response = await async_client.get(
                "/system/diagnostics/knowledge"
            )
            data = response.json()
            assert data["status"] == "empty"
```

### Paso 5: Ejecutar tests

```bash
pytest tests/unit/api/test_diagnostics.py -v
```
Esperado: PASS

### Paso 6: Commit

```bash
git add src/api/routers/diagnostics.py src/core/schemas/api.py src/main.py \
  tests/unit/api/test_diagnostics.py
git commit -m "feat(api): endpoint de diagnóstico de conocimiento global (P2/P4)"
```

---

## Tarea 5: Transparencia RAG Enriquecida en Especialistas (Problema P5)

> Los especialistas registran exactamente qué documentos se usaron para construir el contexto.

**Archivos:**
- Modificar: `src/agents/specialists/cbt/cbt_tool.py:70-74`
- Modificar: `src/agents/specialists/chat/chat_tool.py:60-64`

### Paso 1: Modificar `cbt_tool.py`

Reemplazar el bloque de transparencia RAG (líneas 70-74) por:

```python
        # Transparencia RAG enriquecida (ADR-0025)
        global_sources = [
            r.get("metadata", {}).get("filename", "?")
            for r in global_results
        ]
        logger.info(
            f"[CBT-RAG] Context injection for chat={chat_id}",
            extra={
                "event": "specialist_rag_injection",
                "specialist": "cbt",
                "chat_id": chat_id,
                "global_count": len(global_results),
                "user_count": len(user_results),
                "global_sources": global_sources,
                "total_context_chars": len(knowledge_context),
            },
        )
```

### Paso 2: Modificar `chat_tool.py`

Después de la línea `all_results = global_results + user_results` (línea 59), añadir antes del `if all_results`:

```python
        # Transparencia RAG enriquecida (ADR-0025)
        global_sources = [
            r.get("metadata", {}).get("filename", "?")
            for r in global_results
        ]
        logger.info(
            f"[CHAT-RAG] Context injection for chat={chat_id}",
            extra={
                "event": "specialist_rag_injection",
                "specialist": "chat",
                "chat_id": chat_id,
                "global_count": len(global_results),
                "user_count": len(user_results),
                "global_sources": global_sources,
            },
        )
```

### Paso 3: Verificar tests existentes

```bash
pytest tests/unit/test_cbt_safety.py tests/integration/test_conversational_flow.py -v
```
Esperado: PASS (sin regresión)

### Paso 4: Commit

```bash
git add src/agents/specialists/cbt/cbt_tool.py \
  src/agents/specialists/chat/chat_tool.py
git commit -m "feat(agents): transparencia RAG enriquecida en especialistas CBT/Chat (P5)"
```

---

## Tarea 6: Verificación Integral

**Archivos:** Ninguno (solo ejecución)

### Paso 1: Ejecutar todos los tests nuevos

```bash
pytest tests/unit/memory/test_global_knowledge_loader.py \
  tests/unit/memory/test_knowledge_auditor.py \
  tests/unit/api/test_diagnostics.py -v
```
Esperado: PASS (todos)

### Paso 2: Ejecutar suite completa

```bash
make verify
```
Esperado: PASS (lint + test + arquitectura)

### Paso 3: Verificar límites de LOC

| Archivo | LOC Estimado | Límite | Estado |
|---------|-------------|--------|--------|
| `src/memory/global_knowledge_loader.py` | ~185 | 200 | OK |
| `src/memory/knowledge_auditor.py` | ~120 | 200 | OK |
| `src/memory/vector_memory_manager.py` | ~195 | 200 | OK |
| `src/api/routers/diagnostics.py` | ~90 | 200 | OK |
| `src/core/schemas/api.py` | ~250 | 300 (definición) | OK |
| `src/agents/specialists/cbt/cbt_tool.py` | ~155 | 200 | OK |
| `src/agents/specialists/chat/chat_tool.py` | ~155 | 200 | OK |
| `src/main.py` | ~182 | 200 | OK |

### Paso 4: Commit final

```bash
git add -A
git commit -m "feat(v0.8.3): observabilidad y calidad de conocimiento global completada"
```

---

## Resumen de Cambios por Archivo

| Archivo | Acción | Tarea | Problema |
|---------|--------|-------|----------|
| `adr/ADR-0025-observabilidad-conocimiento-global.md` | Crear | 0 | Todos |
| `src/memory/global_knowledge_loader.py` | Modificar | 1 | P1 |
| `src/memory/knowledge_watcher.py` | Modificar | 1 | P1 |
| `src/memory/knowledge_auditor.py` | Crear | 2 | P2/P4 |
| `src/memory/vector_memory_manager.py` | Modificar | 3 | P3 |
| `src/api/routers/diagnostics.py` | Crear | 4 | P2/P4 |
| `src/core/schemas/api.py` | Modificar | 4 | P2/P4 |
| `src/main.py` | Modificar | 4 | P2/P4 |
| `src/agents/specialists/cbt/cbt_tool.py` | Modificar | 5 | P5 |
| `src/agents/specialists/chat/chat_tool.py` | Modificar | 5 | P5 |
| Tests nuevos (3 archivos) | Crear | 1,2,4 | Todos |

**Total: 5 archivos nuevos, 7 archivos modificados, 7 commits atómicos.**

---

## Uso Post-Implementación

### Monitoreo en tiempo real (Logs)

```bash
# Ver todas las decisiones de ingesta
docker-compose logs -f app | jq 'select(.message | test("INGESTA"))'

# Ver trazas RAG con detalle de fragmentos
docker-compose logs -f app | jq 'select(.event == "rag_retrieval")'

# Ver qué documentos usa cada especialista
docker-compose logs -f app | jq 'select(.event == "specialist_rag_injection")'
```

### Diagnóstico bajo demanda (API)

```bash
# Inventario rápido
curl http://localhost:8000/system/diagnostics/knowledge

# Con verificación de recuperabilidad
curl "http://localhost:8000/system/diagnostics/knowledge?verify=true&sample_query=ansiedad+protocolo"
```

---
*Plan generado a partir del reporte `v0.7.2-analisis-fallo-ingesta-global.md`. Aprobación del usuario requerida antes de ejecutar.*
