# Fix Crítico de Intents y Graph-RAG Data-Driven — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Corregir tres bugs críticos que dejan funcionalidad clave inoperativa: Graph-RAG (ADR-0033) nunca se activa, el skip de RAG en saludos nunca opera, y psicotrading no es alcanzable por el LLM del router.

**Architecture:** Refactor de `context_retriever.py` para Graph-RAG data-driven (por existencia de aristas en `memory_edges`, no por intents hardcodeados). Detección de mensajes casuales por regex sobre texto. Uso de `IntentType` directamente como tipo del parámetro `intent` en el tool del router. Test de anotación de intents como guardia de CI.

**Tech Stack:** Python 3.13, pytest, aiosqlite, LangChain (ChatGroq), re (stdlib), `make verify`

**ADR de referencia:** ADR-0034 (`adr/ADR-0034-graph-rag-data-driven.md`)

---

## Task 1: Usar `IntentType` directamente en routing_tools — BUG-3

**Files:**
- Modify: `src/agents/orchestrator/routing/routing_tools.py:16-27`
- Create: `tests/unit/core/test_intent_annotation.py` (nuevo)

**Step 1: Escribir el test que falla**

En lugar de verificar sincronía entre un `Literal` y el enum (que con este cambio ya no existe), el test valida que la anotación del parámetro es `IntentType` directamente:

```python
"""Tests de anotación de intent en routing_tools."""
import inspect

from src.core.routing_models import IntentType


def test_routing_tools_uses_intent_type_directly() -> None:
    """
    El parámetro 'intent' de route_user_message debe usar IntentType
    como tipo, no un Literal hardcodeado.

    Usar IntentType directamente elimina la fuente del bug BUG-3:
    no hay un segundo lugar que actualizar al añadir un nuevo intent.
    LangChain extrae los valores del enum automáticamente.
    """
    from src.agents.orchestrator.routing.routing_tools import route_user_message

    func = route_user_message.func if hasattr(route_user_message, "func") else route_user_message
    sig = inspect.signature(func)
    intent_param = sig.parameters["intent"]

    assert intent_param.annotation is IntentType, (
        f"Se esperaba IntentType, pero se encontró {intent_param.annotation}. "
        "Usar IntentType directamente evita la desincronización manual del Literal."
    )


def test_all_intent_type_values_are_valid() -> None:
    """
    Verifica que IntentType tenga al menos los valores esperados.
    Si este test falla tras añadir un valor, el cambio es legítimo.
    Si falla tras eliminar un valor, alguien rompió el enum.
    """
    values = {e.value for e in IntentType}
    assert "chat" in values
    assert "psicotrading" in values
    assert len(values) >= 11
```

**Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/core/test_intent_annotation.py -v
```

Esperado: FAIL — actualmente `routing_tools.py` usa `Literal[...]`, no `IntentType`.

**Step 3: Cambiar la anotación en `routing_tools.py`**

De:
```python
from typing import Any, Literal

@tool
async def route_user_message(
    intent: Literal[
        "chat",
        "file_analysis",
        "search",
        "help",
        "task_execution",
        "information_request",
        "planning",
        "document_creation",
        "vulnerability",
        "topic_shift",
    ],
```

A:
```python
from typing import Any
from src.core.routing_models import IntentType

@tool
async def route_user_message(
    intent: IntentType,
```

Eliminar el import de `Literal` si ya no se usa en ninguna otra parte del archivo.

**Step 4: Ejecutar test**

```bash
pytest tests/unit/core/test_intent_annotation.py -v
```

Esperado: PASS.

**Step 5: `make verify`**

```bash
make verify
```

Esperado: 0 errores.

**Step 6: Commit**

```bash
git add src/agents/orchestrator/routing/routing_tools.py tests/unit/core/test_intent_annotation.py
git commit -m "fix(routing): usar IntentType directamente en route_user_message en lugar de Literal hardcodeado (BUG-3, ADR-0034)"
```

---

## Task 2: Reemplazar CASUAL_INTENTS con detección por regex — BUG-2

**Files:**
- Modify: `src/agents/orchestrator/context_retriever.py:14` y líneas 80-96

**Step 1: Escribir test del comportamiento esperado**

En `tests/unit/core/test_casual_detection.py` (crear nuevo):

```python
"""Tests de detección de mensajes casuales en context_retriever."""
import pytest

# Importar la función que vamos a crear
from src.agents.orchestrator.context_retriever import _is_casual_message


@pytest.mark.parametrize("text,expected", [
    # Mensajes casuales (deben retornar True)
    ("hola", True),
    ("hey", True),
    ("Hola!", True),
    ("buenas tardes", True),
    ("ok", True),
    ("gracias", True),
    ("bye", True),
    ("👋", True),
    ("entendido", True),
    # Mensajes no casuales (deben retornar False)
    ("sí", False),            # Una sola palabra pero no casual pattern
    ("no", False),            # Una sola palabra no casual
    ("¿cómo estoy?", False),  # Pregunta no casual
    ("Tengo ansiedad hoy", False),
    ("¿qué debería hacer con mi dieta?", False),
    ("ok, cuéntame más sobre TCC", False),
    # Mensajes de crisis — NUNCA casuales, pero el regex anclado ya los rechaza
    # sin necesidad de lista de exclusión dedicada.
    ("estoy mal", False),
    ("me muero", False),
    ("ayuda", False),
])
def test_is_casual_message(text: str, expected: bool) -> None:
    assert _is_casual_message(text) == expected, f"Para '{text}' esperaba {expected}"
```

**Step 2: Ejecutar test para verificar que falla (función no existe aún)**

```bash
pytest tests/unit/core/test_casual_detection.py -v
```

Esperado: ImportError / AttributeError

**Step 3: Implementar `_is_casual_message` y reemplazar CASUAL_INTENTS**

Reemplazar en `src/agents/orchestrator/context_retriever.py`:

```python
# ELIMINAR esta línea:
CASUAL_INTENTS = {"casual_greeting", "farewell", "acknowledgement"}

# AÑADIR al inicio del archivo (tras los imports):
import re
import unicodedata

_CASUAL_PATTERN = re.compile(
    r"^\s*(hola|hey|buenas?|ey|hi|hello|ok|okey|vale|gracias|"
    r"de nada|bye|hasta|adi[oó]s|chao|entendido|claro|perfecto|"
    r"👋|🙋|👍|✅)\s*[!.?]*\s*$",
    re.IGNORECASE | re.UNICODE,
)

def _is_casual_message(text: str) -> bool:
    """Detecta mensajes triviales que no requieren búsqueda semántica."""
    normalized = unicodedata.normalize("NFC", text)
    return bool(_CASUAL_PATTERN.match(normalized))
```

Y la condición de skip (línea ~80):

```python
    # 2. Condición: Mensajes Conversacionales Triviales
    if (
        _is_casual_message(user_message)
        or payload.get("processing_type") == "conversational_only"
    ):
```

**Step 4: Ejecutar test de casualidad**

```bash
pytest tests/unit/core/test_casual_detection.py -v
```

Esperado: PASS en todos los parametrize

**Step 5: Ejecutar test de anotación de intents**

```bash
pytest tests/unit/core/test_intent_annotation.py::test_all_intent_type_values_are_valid -v
```

Esperado: PASS (CASUAL_INTENTS ya no existe)

**Step 6: `make verify`**

```bash
make verify
```

Esperado: 0 errores de lint, tipo y arquitectura.

**Step 7: Commit**

```bash
git add src/agents/orchestrator/context_retriever.py tests/unit/core/test_casual_detection.py
git commit -m "fix(context-retriever): reemplazar CASUAL_INTENTS hardcodeado por detección regex (BUG-2)"
```

---

## Task 3: Activar Graph-RAG data-driven — BUG-1

**Files:**
- Modify: `src/agents/orchestrator/context_retriever.py:140-152`
- Create: `src/agents/orchestrator/_graph_rag.py` (función auxiliar extraída)

**Step 1: Escribir test de integración del Graph-RAG**

En `tests/unit/memory/test_graph_rag_activation.py` (crear nuevo):

```python
"""Tests de activación data-driven del Graph-RAG."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_graph_rag_activates_when_edges_exist() -> None:
    """Cuando memory_edges tiene aristas para los seed_ids, expand_with_edges debe llamarse."""
    from src.agents.orchestrator.context_retriever import context_retriever_node
    from src.core.schemas.graph import GraphStateV2

    # Mock del manager con fragmentos semánticos que tienen IDs
    mock_manager = MagicMock()
    mock_manager.retrieve_context = AsyncMock(return_value=[
        {"id": 1, "content": "Déficit calórico 400kcal", "score": 0.9},
        {"id": 2, "content": "Irritabilidad los lunes", "score": 0.85},
    ])
    mock_manager.store = MagicMock()

    # Mock de _check_edges_exist retornando True (hay aristas)
    with (
        patch("src.agents.orchestrator.context_retriever.get_vector_memory_manager", return_value=mock_manager),
        patch("src.agents.orchestrator.context_retriever._check_edges_exist", new_callable=AsyncMock, return_value=True) as mock_check,
        patch("src.agents.orchestrator.context_retriever.expand_with_edges", new_callable=AsyncMock, return_value=[{"id": 3, "content": "Gasto impulsivo"}]) as mock_expand,
        patch("src.agents.orchestrator.context_retriever._load_evolution_note", new_callable=AsyncMock, return_value=("nota", True)),
        patch("src.memory.reranker.SemanticReranker.rerank", new_callable=AsyncMock, return_value=[{"id": 1, "content": "Déficit calórico"}]),
    ):
        state = GraphStateV2(
            event=MagicMock(chat_id="123", content="¿cómo afecta mi entrenamiento a mi humor?"),
            payload={"routing_metadata": {"intent": "information_request"}},
        )
        result = await context_retriever_node(state)

    mock_check.assert_awaited_once()
    mock_expand.assert_awaited_once()
    assert result["rag_context"]["graph_fragments"] == [{"id": 3, "content": "Gasto impulsivo"}]


@pytest.mark.asyncio
async def test_graph_rag_skips_when_no_edges() -> None:
    """Cuando no hay aristas en memory_edges, expand_with_edges no debe llamarse."""
    from src.agents.orchestrator.context_retriever import context_retriever_node
    from src.core.schemas.graph import GraphStateV2

    mock_manager = MagicMock()
    mock_manager.retrieve_context = AsyncMock(return_value=[
        {"id": 1, "content": "Texto sin aristas", "score": 0.8},
    ])
    mock_manager.store = MagicMock()

    with (
        patch("src.agents.orchestrator.context_retriever.get_vector_memory_manager", return_value=mock_manager),
        patch("src.agents.orchestrator.context_retriever._check_edges_exist", new_callable=AsyncMock, return_value=False) as mock_check,
        patch("src.agents.orchestrator.context_retriever.expand_with_edges", new_callable=AsyncMock) as mock_expand,
        patch("src.agents.orchestrator.context_retriever._load_evolution_note", new_callable=AsyncMock, return_value=("nota", True)),
        patch("src.memory.reranker.SemanticReranker.rerank", new_callable=AsyncMock, return_value=[{"id": 1, "content": "Texto"}]),
    ):
        state = GraphStateV2(
            event=MagicMock(chat_id="123", content="¿qué tal el día?"),
            payload={"routing_metadata": {"intent": "chat"}},
        )
        result = await context_retriever_node(state)

    mock_check.assert_awaited_once()
    mock_expand.assert_not_awaited()
    assert result["rag_context"]["graph_fragments"] == []
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/memory/test_graph_rag_activation.py -v
```

Esperado: FAIL (función `_check_edges_exist` no existe)

**Step 3: Implementar `_check_edges_exist` y reemplazar la lógica de Graph-RAG**

En `src/agents/orchestrator/context_retriever.py`, añadir la función auxiliar:

```python
async def _check_edges_exist(store: Any, memory_ids: list[int]) -> bool:
    """
    Verifica si existe al menos una arista en memory_edges para los IDs dados.
    Verifica tanto origen_id como destino_id: las aristas son direccionales
    pero nos interesa saber si el fragmento participa en CUALQUIER relación.
    Costo: <5ms si no hay aristas (caso típico en sesiones nuevas).
    """
    if not memory_ids:
        return False
    placeholders = ",".join("?" * len(memory_ids))
    query = (
        f"SELECT 1 FROM memory_edges "
        f"WHERE origen_id IN ({placeholders}) OR destino_id IN ({placeholders}) "
        f"LIMIT 1"
    )
    try:
        # Los parámetros se duplican porque hay dos cláusulas IN
        params = memory_ids + memory_ids
        result = await store.execute(query, params)
        rows = await result.fetchone()
        return rows is not None
    except Exception as e:
        logger.warning(f"Error verificando aristas en memory_edges: {e}")
        return False
```

Y reemplazar el bloque de Graph-RAG (líneas 140-152):

```python
        # Graph-RAG Transversal: Expansión de Grafo (ADR-0033 + ADR-0034)
        # Activación data-driven: si los fragmentos recuperados tienen aristas,
        # expandir el grafo sin discriminar por intent.
        # `expand_with_edges` ya incluye poda por accumulated_weight > 0.3
        # y límite de 8 fragmentos en la CTE recursiva (ver ADR-0034 sección 1b).
        if semantic_fragments:
            try:
                from src.memory.graph_search import expand_with_edges

                seed_ids = [item["id"] for item in semantic_fragments if "id" in item]
                has_edges = await _check_edges_exist(store=manager.store, memory_ids=seed_ids)
                if has_edges:
                    graph_fragments = await expand_with_edges(
                        store=manager.store, seed_memory_ids=seed_ids, max_hops=2
                    )
                    logger.info(
                        f"[CONTEXT-RETRIEVER] Graph-RAG expandido: {len(graph_fragments)} fragmentos de grafo"
                    )
            except Exception as ge:
                logger.warning(f"Error expandiendo grafo en context_retriever: {ge}")
```

**Step 4: Ejecutar tests del Graph-RAG**

```bash
pytest tests/unit/memory/test_graph_rag_activation.py -v
```

Esperado: PASS en ambos tests.

**Step 5: Ejecutar suite completa de unit tests**

```bash
pytest tests/unit/ -v
```

Esperado: 64+ tests passing (los previos más los nuevos).

**Step 6: `make verify`**

```bash
make verify
```

Esperado: 0 errores.

**Step 7: Commit**

```bash
git add src/agents/orchestrator/context_retriever.py tests/unit/memory/test_graph_rag_activation.py
git commit -m "fix(context-retriever): Graph-RAG data-driven — eliminar analytical_intents hardcodeados (BUG-1, ADR-0034)"
```

---

## Task 4: Feedback Loop de Aristas vía ConsolidationWorker — Sistema Vivo

**ADR:** ADR-0034 sección 1c, ADR-0037 sección 5
**Files:**
- Modify: `src/memory/consolidation_worker.py`
- Test: `tests/unit/memory/test_edge_feedback.py` (crear)

**Step 1: Escribir tests de feedback**

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


@pytest.mark.asyncio
async def test_adjust_edge_weights_skips_when_empty() -> None:
    from src.memory.consolidation_worker import _adjust_edge_weights_from_feedback
    mock_store = AsyncMock()
    result = await _adjust_edge_weights_from_feedback(
        store=mock_store, chat_id="123",
        conversation_history=["msg1"], injected_graph_fragments=[],
    )
    assert result == {"reinforced": 0, "decayed": 0}
    mock_store.execute.assert_not_awaited()
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/memory/test_edge_feedback.py -v
```

**Step 3: Implementar en `consolidation_worker.py`**

Añadir al final del archivo: `FEEDBACK_PROMPT`, `_parse_useful_ids`, `_adjust_edge_weights_from_feedback`. El LLM (Gemini Flash via `get_rag_llm()`) evalúa qué fragmentos del grafo inyectados en el contexto fueron pertinentes. Aristas útiles: `peso + 0.05`. Aristas no útiles: `peso - 0.03`. Acotado a `MIN(2.0, ...)` y `MAX(0.0, ...)`.

**Step 4: Ejecutar tests**

```bash
pytest tests/unit/memory/test_edge_feedback.py -v
```

**Step 5: Commit**

```bash
git add src/memory/consolidation_worker.py tests/unit/memory/test_edge_feedback.py
git commit -m "feat(memory): feedback loop de aristas — ConsolidationWorker ajusta pesos de memory_edges basado en utilidad (ADR-0034 s1c, ADR-0037 s5)"
```

---

## Task 5: Corregir versión en pyproject.toml — BUG-5

**Files:**
- Modify: `pyproject.toml`

**Step 1: Actualizar versión**

Cambiar `version = "0.7.2"` → `version = "0.9.0"` en la sección `[project]`.

**Step 2: Verificar**

```bash
grep 'version' pyproject.toml | head -3
```

Esperado: `version = "0.9.0"`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: sincronizar versión pyproject.toml con v0.9.0 (BUG-5)"
```

---

## Task 6: Test final de regresión completo

**Step 1: Ejecutar suite completa con verify**

```bash
make verify
```

Esperado: lint OK, types OK, architecture OK, ≥64 tests passing.

**Step 2: Verificar cobertura de los nuevos tests**

```bash
pytest tests/unit/core/test_intent_annotation.py tests/unit/core/test_casual_detection.py tests/unit/memory/test_graph_rag_activation.py -v --tb=short
```

Esperado: todos los tests del plan pasan.

**Step 3: Commit final si hay cambios residuales**

```bash
git add -A
git status  # Verificar que solo hay archivos relacionados con el plan
git commit -m "fix(intents): usar IntentType como anotación del router y tests de detección casual (ADR-0034)"
```

---

## Verificación de aceptación

El plan está completamente implementado cuando:

1. `make verify` pasa al 100%.
2. `pytest tests/unit/core/test_intent_annotation.py -v` — todos pasan.
3. `pytest tests/unit/core/test_casual_detection.py -v` — todos pasan.
4. `pytest tests/unit/memory/test_graph_rag_activation.py -v` — todos pasan.
5. `pytest tests/unit/memory/test_edge_feedback.py -v` — todos pasan.
6. `grep "analytical_intents" src/agents/orchestrator/context_retriever.py` — sin resultados.
7. `grep "CASUAL_INTENTS" src/agents/orchestrator/context_retriever.py` — sin resultados.
8. `grep "IntentType" src/agents/orchestrator/routing/routing_tools.py` — 1 resultado (el import).
9. `grep 'Literal' src/agents/orchestrator/routing/routing_tools.py | grep -i intent` — sin resultados (ya no hay Literal de intents).
10. `grep 'version' pyproject.toml | grep "0.9.0"` — 1 resultado.
