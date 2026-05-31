# Bloque D: Aprendizaje Continuo y Skills Dinámicos — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Implementar el bucle de aprendizaje continuo (Bloque D del Plan Maestro): nudge de memoria post-turno, session search tool, curador de skills, compresión de contexto, **feedback de aristas del grafo vía ConsolidationWorker (sistema vivo)**, gating condicional de skills, y hot-reload. El Skill Workshop es la última fase y la más opcional.

**Architecture:** Nuevos workers/tools que se conectan a infraestructura existente (Redis buffer, FTS5, ConsolidationWorker, KnowledgeWatcher, PersonalityManager). Sin nuevas tablas de schema. Sin nuevas dependencias externas.

**Tech Stack:** Python 3.13, pytest, asyncio, aiosqlite (FTS5), redis, LangChain, re (stdlib), `make verify`

**ADRs de referencia:** ADR-0037 (Aprendizaje Continuo), ADR-0038 (Skills Dinámicos)

**Orden de ejecución:** D.1a (nudge) → D.1b (session search) → D.1c (curador) → D.1d (compresión) → **D.1e (edge feedback)** → D.2a (gating) → D.2b (hot-reload) → D.2c (Skill Workshop — OPCIONAL)

---

## Task D.1a: Nudge de Memoria Post-Turno

**Files:**
- Create: `src/memory/nudge_worker.py`
- Modify: `src/agents/orchestrator/` — hook post-respuesta (leer antes de modificar)
- Test: `tests/unit/memory/test_nudge_worker.py`

**Step 1: Escribir tests del nudge worker**

```python
"""Tests del nudge de memoria post-turno."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_nudge_skips_if_not_nudge_turn() -> None:
    """El nudge solo se activa cada N turnos. Para turnos intermedios, no hace nada."""
    from src.memory.nudge_worker import memory_nudge_worker

    with patch("src.memory.nudge_worker._get_turn_count", new_callable=AsyncMock, return_value=2):
        result = await memory_nudge_worker(chat_id="123", nudge_every_n=3)

    assert result == {"extracted": 0, "reason": "not_nudge_turn"}


@pytest.mark.asyncio
async def test_nudge_extracts_facts_on_nudge_turn() -> None:
    """En el turno de nudge, extrae hechos y los persiste."""
    from src.memory.nudge_worker import memory_nudge_worker

    mock_facts = [
        {"content": "Prefiere sesiones de 45 minutos", "type": "preference", "confidence": 0.85},
    ]

    with (
        patch("src.memory.nudge_worker._get_turn_count", new_callable=AsyncMock, return_value=3),
        patch("src.memory.nudge_worker._get_recent_messages", new_callable=AsyncMock,
              return_value=[{"role": "user", "content": "Prefiero sesiones de 45 minutos"}]),
        patch("src.memory.nudge_worker._extract_lightweight_facts", new_callable=AsyncMock,
              return_value=mock_facts) as mock_extract,
        patch("src.memory.nudge_worker._save_fact_if_new", new_callable=AsyncMock,
              return_value=True) as mock_save,
    ):
        result = await memory_nudge_worker(chat_id="123", nudge_every_n=3)

    mock_extract.assert_awaited_once()
    mock_save.assert_awaited_once()
    assert result["extracted"] == 1


@pytest.mark.asyncio
async def test_nudge_deduplicates_existing_facts() -> None:
    """No persiste facts que ya existen (similitud FTS5 > umbral)."""
    from src.memory.nudge_worker import memory_nudge_worker

    with (
        patch("src.memory.nudge_worker._get_turn_count", new_callable=AsyncMock, return_value=3),
        patch("src.memory.nudge_worker._get_recent_messages", new_callable=AsyncMock,
              return_value=[{"role": "user", "content": "Prefiero mañanas"}]),
        patch("src.memory.nudge_worker._extract_lightweight_facts", new_callable=AsyncMock,
              return_value=[{"content": "Prefiere mañanas", "type": "preference"}]),
        patch("src.memory.nudge_worker._save_fact_if_new", new_callable=AsyncMock,
              return_value=False),  # Ya existe
    ):
        result = await memory_nudge_worker(chat_id="123", nudge_every_n=3)

    assert result["extracted"] == 0
    assert result.get("deduplicated") == 1
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/memory/test_nudge_worker.py -v
```

Esperado: ImportError (módulo no existe).

**Step 3: Implementar `src/memory/nudge_worker.py`**

```python
# src/memory/nudge_worker.py
"""
Nudge de Memoria Post-Turno.

Extrae hechos de los últimos N mensajes cada NUDGE_EVERY_N_TURNS turnos,
complementando el ConsolidationWorker sin reemplazarlo.
"""
import logging
from typing import Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

NUDGE_EVERY_N_TURNS: int = 3
_NUDGE_PROMPT = """
Analiza estos mensajes recientes y extrae ÚNICAMENTE preferencias explícitas y hechos concretos verificables.
NO generes resúmenes ni análisis. Solo hechos directos del usuario.

Mensajes:
{messages}

Responde con una lista JSON de objetos: [{"content": "...", "type": "preference|fact", "confidence": 0.0-1.0}]
Si no hay hechos nuevos dignos de guardar, responde con: []
"""


async def _get_turn_count(chat_id: str, redis_conn: Any) -> int:
    """Incrementa y retorna el contador de turnos del chat."""
    key = f"chat:turn_count:{chat_id}"
    count = await redis_conn.incr(key)
    await redis_conn.expire(key, 86400)  # TTL 24h
    return int(count)


async def _get_recent_messages(chat_id: str, redis_conn: Any, limit: int = 6) -> list[dict]:
    """Obtiene los últimos `limit` mensajes del buffer Redis."""
    key = f"chat:buffer:{chat_id}"
    raw = await redis_conn.lrange(key, -limit, -1)
    messages = []
    for item in raw:
        try:
            import json
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            messages.append(json.loads(item))
        except Exception:
            pass
    return messages


async def _extract_lightweight_facts(messages: list[dict]) -> list[dict]:
    """Usa get_fast_llm para extraer hechos concretos de los mensajes."""
    import json
    from src.core.engine import get_fast_llm

    if not messages:
        return []

    formatted = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
    prompt = _NUDGE_PROMPT.format(messages=formatted)

    try:
        llm = get_fast_llm()
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        # Extraer JSON del response
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        logger.warning(f"[NUDGE] Error extrayendo facts: {e}")
    return []


async def _save_fact_if_new(
    chat_id: str,
    fact: dict,
    store: Any,
) -> bool:
    """
    Guarda el fact si no existe uno similar (deduplicación por FTS5).
    Retorna True si se guardó, False si era duplicado.
    """
    from src.memory.keyword_search import search_by_keyword

    content = fact.get("content", "")
    if not content:
        return False

    # Búsqueda FTS5 para detectar duplicados
    existing = await search_by_keyword(
        store=store,
        query=content,
        namespace=f"user_{chat_id}",
        limit=1,
    )

    if existing and len(existing) > 0:
        # Heurística simple: si el primer resultado tiene >80% de palabras en común, es duplicado
        existing_words = set(existing[0].get("content", "").lower().split())
        new_words = set(content.lower().split())
        if len(new_words) > 0:
            overlap = len(existing_words & new_words) / len(new_words)
            if overlap > 0.8:
                logger.debug(f"[NUDGE] Fact duplicado (overlap={overlap:.2f}): {content[:50]}")
                return False

    # Guardar el fact
    from src.memory.ingestion_pipeline import IngestionPipeline
    pipeline = IngestionPipeline(store=store)
    await pipeline.save_knowledge(
        chat_id=chat_id,
        content=content,
        knowledge_type=fact.get("type", "fact"),
        confidence=fact.get("confidence", 0.7),
    )
    return True


async def memory_nudge_worker(
    chat_id: str,
    nudge_every_n: int = NUDGE_EVERY_N_TURNS,
    redis_conn: Any = None,
    store: Any = None,
) -> dict:
    """
    Worker de nudge de memoria post-turno.

    Args:
        chat_id: ID del chat del usuario.
        nudge_every_n: Activar cada N turnos.
        redis_conn: Conexión Redis (inyectada).
        store: SQLite store (inyectado).

    Returns:
        Dict con resultado: {"extracted": N, "deduplicated": M, "reason": "..."}
    """
    if redis_conn is None:
        from src.core.dependencies import redis_connection
        redis_conn = redis_connection

    if redis_conn is None:
        return {"extracted": 0, "reason": "redis_unavailable"}

    turn_count = await _get_turn_count(chat_id, redis_conn)

    if turn_count % nudge_every_n != 0:
        return {"extracted": 0, "reason": "not_nudge_turn"}

    messages = await _get_recent_messages(chat_id, redis_conn)
    if not messages:
        return {"extracted": 0, "reason": "no_messages"}

    facts = await _extract_lightweight_facts(messages)

    if store is None:
        from src.core.dependencies import get_sqlite_store
        store = get_sqlite_store()

    extracted = 0
    deduplicated = 0
    for fact in facts:
        saved = await _save_fact_if_new(chat_id, fact, store)
        if saved:
            extracted += 1
        else:
            deduplicated += 1

    logger.info(f"[NUDGE] chat={chat_id} turn={turn_count}: extracted={extracted}, deduplicated={deduplicated}")
    return {"extracted": extracted, "deduplicated": deduplicated, "reason": "nudge_executed"}
```

**Step 4: Ejecutar tests**

```bash
pytest tests/unit/memory/test_nudge_worker.py -v
```

Esperado: PASS en todos.

**Step 5: `make verify`**

```bash
make verify
```

**Step 6: Commit**

```bash
git add src/memory/nudge_worker.py tests/unit/memory/test_nudge_worker.py
git commit -m "feat(memory): nudge de memoria post-turno — extracción ligera entre consolidaciones (ADR-0037)"
```

---

## Task D.1b: Session Search Tool

**Files:**
- Create: `src/tools/session_search.py`
- Modify: `src/personality/skills/chat/tools.py` — registrar el tool
- Test: `tests/unit/tools/test_session_search.py`

**Step 1: Escribir test**

```python
"""Tests de búsqueda en historial de conversaciones."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_conversation_history_returns_results() -> None:
    """La búsqueda debe retornar fragmentos de conversación relevantes."""
    from src.tools.session_search import search_conversation_history

    mock_results = [
        {"content": "Hablamos sobre déficit calórico", "created_at": "2026-05-20T10:00:00"},
    ]

    with patch("src.tools.session_search._keyword_search_conversations",
               new_callable=AsyncMock, return_value=mock_results):
        result = await search_conversation_history.ainvoke({
            "query": "dieta",
            "chat_id": "123",
            "days_back": 30,
        })

    assert "déficit calórico" in result


@pytest.mark.asyncio
async def test_search_conversation_history_empty_returns_message() -> None:
    """Si no hay resultados, retornar mensaje informativo (no None ni lista vacía)."""
    from src.tools.session_search import search_conversation_history

    with patch("src.tools.session_search._keyword_search_conversations",
               new_callable=AsyncMock, return_value=[]):
        result = await search_conversation_history.ainvoke({
            "query": "inexistente",
            "chat_id": "123",
            "days_back": 30,
        })

    assert isinstance(result, str)
    assert len(result) > 0  # Debe retornar algún mensaje, no string vacío
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/tools/test_session_search.py -v
```

**Step 3: Implementar `src/tools/session_search.py`**

```python
# src/tools/session_search.py
"""
Session Search Tool — Búsqueda en historial de conversaciones vía FTS5.

Permite a MAGI consultar conversaciones pasadas cuando el usuario pregunta
por algo que se discutió en sesiones anteriores.
"""
import logging
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


async def _keyword_search_conversations(
    query: str,
    namespace: str,
    days_back: int,
    limit: int,
    store: object | None = None,
) -> list[dict]:
    """
    Busca en conversaciones usando FTS5 con filtro por tipo y fecha en SQL.

    NOTA: Usa store.execute() directamente con raw SQL en lugar de
    KeywordSearch.search() porque esta última no expone type_filter.
    Filtrar en SQL es más eficiente que traer N×3 registros para
    descartarlos en Python.
    """
    from src.core.dependencies import get_sqlite_store

    if store is None:
        store = get_sqlite_store()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    sql = """
        SELECT m.id, m.content, m.created_at, m.memory_type
        FROM memories m
        JOIN memories_fts fts ON m.id = fts.rowid
        WHERE m.namespace = ?
          AND m.is_active = 1
          AND m.memory_type = 'conversation'
          AND m.created_at >= ?
          AND fts.content MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        cursor = await store.execute(sql, [namespace, cutoff, query, limit])
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "content": r[1],
                "created_at": r[2],
                "memory_type": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"[SESSION-SEARCH] Error en busqueda FTS5: {e}")
        return []


def _format_conversation_results(results: list[dict]) -> str:
    """Formatea resultados de conversación para el prompt."""
    if not results:
        return "No encontré conversaciones relevantes en el período solicitado."

    lines = [f"Encontré {len(results)} fragmento(s) relevante(s) de conversaciones previas:\n"]
    for i, r in enumerate(results, 1):
        content = r.get("content", "")[:300]
        created = r.get("created_at", "")[:10]  # Solo fecha
        lines.append(f"{i}. [{created}] {content}")

    return "\n".join(lines)


@tool
async def search_conversation_history(
    query: str,
    chat_id: str,
    days_back: int = 30,
) -> str:
    """
    Busca en el historial de conversaciones del usuario por palabras clave.

    Usar cuando el usuario pregunta por algo que se discutió en sesiones anteriores.
    Ejemplos: '¿qué hablamos sobre mi dieta la semana pasada?',
              '¿recuerdas cuando mencioné el gimnasio?'

    Args:
        query: Términos de búsqueda (palabras clave del tema a buscar).
        chat_id: ID del chat del usuario.
        days_back: Número de días hacia atrás a buscar (default: 30).

    Returns:
        Fragmentos de conversación relevantes formateados como texto.
    """
    try:
        results = await _keyword_search_conversations(
            query=query,
            namespace=f"user_{chat_id}",
            days_back=days_back,
            limit=5,
        )
        return _format_conversation_results(results)
    except Exception as e:
        logger.warning(f"[SESSION-SEARCH] Error buscando conversaciones: {e}")
        return "No pude buscar en el historial en este momento."
```

**Step 4: Registrar en `src/personality/skills/chat/tools.py`**

Leer el archivo primero, luego añadir el import del tool.

**Step 5: Ejecutar tests**

```bash
pytest tests/unit/tools/test_session_search.py -v
```

**Step 6: `make verify`**

```bash
make verify
```

**Step 7: Commit**

```bash
git add src/tools/session_search.py src/personality/skills/chat/tools.py tests/unit/tools/test_session_search.py
git commit -m "feat(tools): session search tool — búsqueda FTS5 en historial de conversaciones (ADR-0037)"
```

---

## Task D.2a: Gating Condicional de Skills

**Files:**
- Modify: `src/personality/skill_loader.py`
- Modify: `src/personality/skill_parser.py` — añadir campo `requires` al schema
- Test: `tests/unit/personality/test_skill_gating.py`

**Step 1: Leer `skill_loader.py` y `skill_parser.py`**

Antes de modificar, leer ambos archivos completos para entender la estructura actual.

**Step 2: Escribir tests de gating**

```python
"""Tests de gating condicional de skills."""
import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile


def test_skill_loads_when_no_requires() -> None:
    """Un skill sin sección `requires` siempre se carga."""
    from src.personality.skill_loader import _check_requirements
    assert _check_requirements({}) is True


def test_skill_blocked_when_env_missing() -> None:
    """Un skill con `requires.env` no se carga si la variable no está configurada."""
    from src.personality.skill_loader import _check_requirements
    with patch.dict("os.environ", {}, clear=False):
        # Asegurar que la variable no existe
        import os
        os.environ.pop("NONEXISTENT_API_KEY_XYZ", None)
        result = _check_requirements({"env": ["NONEXISTENT_API_KEY_XYZ"]})
    assert result is False


def test_skill_loads_when_env_present() -> None:
    """Un skill con `requires.env` se carga si la variable está configurada."""
    from src.personality.skill_loader import _check_requirements
    with patch.dict("os.environ", {"MY_TEST_KEY": "some_value"}):
        result = _check_requirements({"env": ["MY_TEST_KEY"]})
    assert result is True


def test_skill_blocked_when_package_missing() -> None:
    """Un skill con `requires.python_packages` no se carga si el paquete no existe."""
    from src.personality.skill_loader import _check_requirements
    result = _check_requirements({"python_packages": ["nonexistent_package_xyz_abc"]})
    assert result is False


def test_skill_loads_when_package_present() -> None:
    """Un skill con `requires.python_packages` se carga si el paquete existe."""
    from src.personality.skill_loader import _check_requirements
    result = _check_requirements({"python_packages": ["json"]})  # stdlib siempre disponible
    assert result is True
```

**Step 3: Implementar `_check_requirements` en `skill_loader.py`**

Añadir la función al módulo (leer primero para elegir el lugar correcto):

```python
import importlib.util
import os
import shutil


def _check_requirements(requires: dict) -> bool:
    """
    Verifica que los requisitos de un skill están disponibles.

    Usa importlib.util.find_spec() en lugar de importlib.import_module()
    para verificar existencia de paquetes Python SIN ejecutarlos.
    import_module() ejecuta side effects al importar (signal handlers,
    conexiones, etc.), lo cual es peligroso durante la carga de skills.

    Args:
        requires: Dict con claves opcionales: env, python_packages, bins.

    Returns:
        True si todos los requisitos están satisfechos, False si alguno falta.
    """
    for env_var in requires.get("env", []):
        if not os.environ.get(env_var):
            logger.debug(f"[SKILL-LOADER] Requisito env no satisfecho: {env_var}")
            return False

    for package in requires.get("python_packages", []):
        if importlib.util.find_spec(package) is None:
            logger.debug(f"[SKILL-LOADER] Requisito Python no instalado: {package}")
            return False

    for binary in requires.get("bins", []):
        if not shutil.which(binary):
            logger.debug(f"[SKILL-LOADER] Binario no encontrado en PATH: {binary}")
            return False

    return True
```

**Step 4: Integrar `_check_requirements` en la carga de skills**

En la función que carga skills individuales (leer primero para identificar el punto exacto), añadir el check:

```python
requires = skill_manifest.get("requires", {})
if not _check_requirements(requires):
    logger.info(f"[SKILL-LOADER] Skill '{skill_id}' deshabilitado por requisitos no satisfechos")
    skill.status = "disabled"
    # No registrar en PersonalityManager activo
    continue
```

**Step 5: Ejecutar tests**

```bash
pytest tests/unit/personality/test_skill_gating.py -v
```

**Step 6: `make verify`**

```bash
make verify
```

**Step 7: Commit**

```bash
git add src/personality/skill_loader.py tests/unit/personality/test_skill_gating.py
git commit -m "feat(personality): gating condicional de skills por env/packages/bins (ADR-0038)"
```

---

## Task D.2b: Hot-Reload de Skills (Extender KnowledgeWatcher)

**Files:**
- Modify: `src/memory/knowledge_watcher.py`
- Test: `tests/unit/memory/test_skill_hot_reload.py`

**Step 1: Leer `knowledge_watcher.py`**

Entender la estructura actual del watcher antes de modificarlo.

**Step 2: Añadir observación de directorio de skills**

Añadir `storage/skills/` a los directorios observados. Solo en `storage/skills/` (no en `src/personality/skills/` en producción).

**Step 3: Manejar evento de cambio en SKILL.md**

Cuando un archivo `SKILL.md` cambia:
1. Re-parsear con `skill_parser.parse()`.
2. Validar YAML (si falla, loguear y mantener versión anterior).
3. Si válido, actualizar en `PersonalityManager` vía evento o llamada directa.
4. Publicar `skill.reloaded` en el bus de eventos.

**Step 4: Commit**

```bash
git add src/memory/knowledge_watcher.py tests/unit/memory/test_skill_hot_reload.py
git commit -m "feat(personality): hot-reload de skills — KnowledgeWatcher observa storage/skills/ (ADR-0038)"
```

---

## Task D.1c: Curador de Skills (Scheduler semanal)

**Files:**
- Create: `src/personality/skill_curator.py`
- Modify: `src/agents/scheduler/` — registrar tarea semanal
- Test: `tests/unit/personality/test_skill_curator.py`

**Step 1: Implementar `skill_curator.py`**

Estructura básica:

```python
# src/personality/skill_curator.py
"""
Curador automático de skills.

Worker semanal que gestiona el ciclo de vida de skills:
- >30 días sin uso → marcar como stale
- >90 días sin uso → archivar (.archive/)
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STALE_DAYS = 30
ARCHIVE_DAYS = 90
SKILLS_DIR = Path("src/personality/skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"
USER_SKILLS_DIR = Path("storage/skills/user")


async def run_skill_curator(
    dry_run: bool = False,
    redis_conn: object | None = None,
) -> dict:
    """
    Ejecuta el curador de skills.

    Args:
        dry_run: Si True, solo reporta sin mover archivos.
        redis_conn: Conexión Redis para leer métricas de uso.

    Returns:
        Reporte: {"stale": [...], "archived": [...], "active": [...]}
    """
    # Implementar según la lógica del ADR-0037
    ...
```

**Step 2: Registrar en scheduler existente**

Leer `src/agents/scheduler/` para entender cómo se registran tareas periódicas, luego añadir la tarea semanal del curador.

**Step 3: Tests**

```python
@pytest.mark.asyncio
async def test_curator_dry_run_reports_stale_skills():
    """En dry_run, el curador reporta skills stale sin moverlos."""
    from src.personality.skill_curator import run_skill_curator
    # Mock de las métricas de uso para simular un skill con 45 días de inactividad
    with patch("src.personality.skill_curator._get_skill_last_used",
               new_callable=AsyncMock,
               return_value=datetime.now(timezone.utc) - timedelta(days=45)):
        report = await run_skill_curator(dry_run=True)

    assert len(report["stale"]) > 0
    assert len(report["archived"]) == 0  # dry_run: no archivados
```

**Step 4: `make verify` + commit**

```bash
make verify
git add src/personality/skill_curator.py tests/unit/personality/test_skill_curator.py
git commit -m "feat(personality): curador automático de skills — ciclo de vida stale/archived (ADR-0037)"
```

---

## Task D.1d: Compresión de Contexto por LLM

**Files:**
- Create: `src/core/context_compressor.py`
- Test: `tests/unit/core/test_context_compressor.py`

**Step 1: Implementar `context_compressor.py`**

```python
# src/core/context_compressor.py
"""
Compresión de contexto conversacional por LLM.

Cuando el historial se acerca al límite de tokens, resume el bloque medio
preservando los primeros y últimos mensajes.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_LIMIT = 6000
PRESERVE_START = 3
PRESERVE_END = 5


def _estimate_tokens(messages: list[dict]) -> int:
    """Estimación rápida: chars // 4."""
    return sum(len(m.get("content", "")) for m in messages) // 4


async def compress_context_if_needed(
    messages: list[dict],
    token_limit: int = DEFAULT_TOKEN_LIMIT,
    preserve_start: int = PRESERVE_START,
    preserve_end: int = PRESERVE_END,
) -> list[dict]:
    """
    Comprime el contexto conversacional si supera el 80% del límite de tokens.

    Args:
        messages: Lista de mensajes de la conversación.
        token_limit: Límite de tokens del modelo.
        preserve_start: Número de mensajes iniciales a preservar.
        preserve_end: Número de mensajes finales a preservar.

    Returns:
        Lista de mensajes (posiblemente con bloque medio comprimido).
    """
    estimated = _estimate_tokens(messages)
    if estimated < token_limit * 0.8:
        return messages

    start = messages[:preserve_start]
    end = messages[-preserve_end:]
    middle = messages[preserve_start:len(messages) - preserve_end]

    if not middle:
        return messages

    logger.info(
        f"[COMPRESSOR] Comprimiendo contexto: {estimated} tokens estimados "
        f"(límite {token_limit}). Bloque medio: {len(middle)} mensajes."
    )

    summary = await _summarize_messages(middle)
    summary_message = {
        "role": "system",
        "content": f"[Resumen de conversación anterior]\n{summary}",
    }
    return start + [summary_message] + end


async def _summarize_messages(messages: list[dict]) -> str:
    """Resume el bloque de mensajes usando get_fast_llm."""
    from src.core.engine import get_fast_llm

    formatted = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')[:500]}"
        for m in messages
    )
    prompt = (
        "Resume esta parte de la conversación en 3-5 oraciones, "
        "preservando los hechos clave y el contexto emocional:\n\n" + formatted
    )

    try:
        llm = get_fast_llm()
        response = await llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.warning(f"[COMPRESSOR] Error resumiendo contexto: {e}")
        return f"[{len(messages)} mensajes omitidos por límite de contexto]"
```

**Step 2: Tests**

```python
@pytest.mark.asyncio
async def test_compression_skips_when_under_limit():
    """Si el contexto está bajo el límite, retornar mensajes sin cambios."""
    from src.core.context_compressor import compress_context_if_needed
    messages = [{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "Hola!"}]
    result = await compress_context_if_needed(messages, token_limit=10000)
    assert result == messages


@pytest.mark.asyncio
async def test_compression_inserts_summary_when_over_limit():
    """Cuando supera el límite, insertar un mensaje de resumen en el bloque medio."""
    from src.core.context_compressor import compress_context_if_needed
    # Crear suficientes mensajes para superar el 80% del límite pequeño
    messages = [{"role": "user", "content": "x" * 100}] * 20

    with patch("src.core.context_compressor._summarize_messages",
               new_callable=AsyncMock, return_value="Resumen del bloque"):
        result = await compress_context_if_needed(messages, token_limit=100)

    # Debe haber un mensaje de resumen
    summary_msgs = [m for m in result if "Resumen de conversación anterior" in m.get("content", "")]
    assert len(summary_msgs) == 1
    assert len(result) < len(messages)
```

**Step 3: `make verify` + commit**

```bash
make verify
git add src/core/context_compressor.py tests/unit/core/test_context_compressor.py
git commit -m "feat(core): compresión de contexto conversacional por LLM — preserva coherencia en sesiones largas (ADR-0037)"
```

---

## Task D.1e: Feedback de Aristas del Grafo — Sistema Vivo

**ADR:** ADR-0034 sección 1c, ADR-0037 sección 5
**Files:**
- Modify: `src/memory/consolidation_worker.py`
- Test: `tests/unit/memory/test_edge_feedback.py` (crear si no se creó en plan fix-intents)

**Step 1: Verificar si el test ya existe**

```bash
ls tests/unit/memory/test_edge_feedback.py
```

Si existe (creado por el plan `fix-intents-graph-rag`), saltar a Step 4. Si no, crearlo:

```python
"""Tests del feedback loop de aristas."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_adjust_edge_weights_reinforces_useful() -> None:
    from src.memory.consolidation_worker import _adjust_edge_weights_from_feedback
    mock_store = AsyncMock()
    fragments = [
        {"id": 1, "edge_id": 42, "content": "Útil"},
        {"id": 2, "edge_id": 43, "content": "Ruido"},
    ]
    with patch("src.memory.consolidation_worker.get_rag_llm",
               return_value=AsyncMock(ainvoke=AsyncMock(
                   return_value=type("r", (), {"content": '{"useful_ids": [1]}'})()
               ))):
        result = await _adjust_edge_weights_from_feedback(
            store=mock_store, chat_id="123",
            conversation_history=["msg1"], injected_graph_fragments=fragments,
        )
    assert result["reinforced"] == 1
    assert result["decayed"] == 1
```

**Step 2: Ejecutar tests**

```bash
pytest tests/unit/memory/test_edge_feedback.py -v
```

**Step 3: Commit**

```bash
git add tests/unit/memory/test_edge_feedback.py
git commit -m "test(memory): feedback loop de aristas del grafo (ADR-0034 s1c, ADR-0037 s5)"
```

**Nota:** La implementación de `_adjust_edge_weights_from_feedback` en `consolidation_worker.py` ya fue incluida en el plan `fix-intents-graph-rag` (Task 4). Este task solo añade los tests complementarios si el otro plan aún no se ha ejecutado.

---

## Verificación final de aceptación (Bloque D)

El bloque D está implementado cuando:

1. `make verify` pasa al 100%.
2. `pytest tests/unit/memory/test_nudge_worker.py -v` — PASS.
3. `pytest tests/unit/tools/test_session_search.py -v` — PASS.
4. `pytest tests/unit/personality/test_skill_gating.py -v` — PASS.
5. `pytest tests/unit/personality/test_skill_curator.py -v` — PASS.
6. `pytest tests/unit/core/test_context_compressor.py -v` — PASS.
7. `pytest tests/unit/memory/test_edge_feedback.py -v` — PASS.
8. `ls src/memory/nudge_worker.py src/tools/session_search.py src/personality/skill_curator.py src/core/context_compressor.py` — todos existen.

### Prioridad de implementación

El Skill Workshop (D.2c — auto-creación por LLM) es **opcional en v0.9.x**. Implementar solo cuando D.1a-D.2b estén estables en producción. La auto-generación de skills requiere revisión humana adicional (aprobación via Telegram) antes de activarse.
