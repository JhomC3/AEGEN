# Plan de Reparación de Memoria y Cognición (v0.8.1)

> **Para Agentes:** SKILL REQUERIDO: Usar `executing-plans` para implementar este plan tarea por tarea.

**Meta:** Eliminar las 4 causas raíz identificadas en el informe forense `v0.7.2-analisis-forense-alucinaciones.md`: amnesia por JSON corrupto, alucinaciones por inferencia, fracturas de enrutamiento terapéutico, y saturación de API por tareas en segundo plano.

**Arquitectura:** Se aplican 4 capas defensivas: (1) Resiliencia JSON con sanitización y validación en la capa de persistencia, (2) Eliminación de hechos inferidos del pipeline de memoria, reteniendo solo hechos explícitos, (3) Contexto de sesión terapéutica en el Router para evitar cambios bruscos de especialista, (4) Regulación de tareas en segundo plano para evitar saturación de API.

**Stack Afectado:** Python 3.12, aiosqlite, Pydantic v2, LangChain, Redis, SQLite, LangGraph.

**ADR Relacionado:** ADR-0024 (a crear en este plan).

**Reporte Base:** `docs/reportes/v0.7.2-analisis-forense-alucinaciones.md`

---

## Diagnóstico: Mapa de Causas Raíz

| ID | Error del Reporte | Causa Raíz | Archivos Afectados | Severidad |
|----|-------------------|------------|---------------------|-----------|
| A | Amnesia (JSON corrupto) | `json.loads()` sin sanitización en `profile_repo.py:52`. Un carácter inválido (comilla simple) causa fallback a perfil vacío. | `src/memory/repositories/profile_repo.py`, `src/memory/knowledge_base.py`, `src/core/profile_manager.py` | **Crítica** |
| B | Alucinación Compuesta | `fact_extractor.py:29-30` instruye al LLM a crear hechos `inferred`. Estos se almacenan en RAG y se recuperan como "confirmados". `knowledge_formatter.py` los etiqueta como hipótesis pero el LLM los trata como hechos. | `src/memory/fact_extractor.py`, `src/agents/utils/knowledge_formatter.py`, `src/memory/vector_memory_manager.py` | **Crítica** |
| C | Fractura de Personalidad | `enhanced_router.py:95-129` no considera el estado de la sesión activa. Una queja del usuario durante sesión CBT se clasifica como `CHAT`, transfiriendo al `chat_specialist` cuyo tono es incompatible. | `src/agents/orchestrator/routing/enhanced_router.py`, `src/agents/orchestrator/routing/routing_prompts.py`, `src/agents/orchestrator/routing/routing_utils.py` | **Alta** |
| D | Loop de Reintentos | La extracción incremental de hechos en segundo plano (`incremental_extractor.py`) satura la cuota de API, retrasando la corrección de datos corruptos. | `src/memory/services/incremental_extractor.py`, `src/memory/long_term_memory.py` | **Media** |

---

## Tarea 0: ADR-0024 - Decisión Arquitectónica

**Archivos:**
- Crear: `adr/ADR-0024-reparacion-memoria-cognicion.md`

**Paso 1: Crear el ADR**

```markdown
# ADR-0024: Reparación de Memoria y Cognición (Post-Mortem v0.7.2)

- **Fecha:** 2026-02-12
- **Estado:** Aceptado

## Contexto

El informe forense `v0.7.2-analisis-forense-alucinaciones.md` documentó un fallo
en cascada con 4 vectores de ataque: (A) JSON corrupto en SQLite causando amnesia
total del perfil, (B) hechos inferidos por el LLM almacenados como datos confirmados
causando alucinaciones persistentes, (C) el Router cambiando de especialista
terapéutico a genérico durante una crisis, y (D) saturación de API por tareas de
fondo retrasando la autocorrección.

## Decisión

1. **Resiliencia JSON**: Añadir sanitización (`ast.literal_eval` fallback +
   regex de comillas) y validación Pydantic en `ProfileRepository.load_profile()`
   y `KnowledgeBaseManager.load_knowledge()`. Nunca retornar `None` sin intentar
   reparación.

2. **Solo Hechos Explícitos**: Modificar el prompt de `FactExtractor` para
   prohibir la clasificación `inferred`. Solo se almacenan datos que el usuario
   dijo literalmente (`explicit`). Añadir filtro de `confidence >= 0.8` antes
   de guardar.

3. **Sesión Terapéutica Sticky**: Introducir el concepto de `active_therapeutic_session`
   en el Router. Cuando CBT está activo y el usuario expresa frustración/queja,
   se mantiene en CBT con acción `handle_resistance` en vez de redirigir a Chat.

4. **Regulación de Tareas de Fondo**: Añadir un semáforo
   (`asyncio.Semaphore(1)`) en la extracción incremental para limitar
   la concurrencia a una sola tarea, descartando invocaciones redundantes
   y evitando saturación de cuota API.

## Consecuencias

### Positivas
- Eliminación de amnesia por errores de formato JSON.
- Eliminación de alucinaciones persistentes por hechos inferidos.
- Continuidad terapéutica durante sesiones CBT.
- Estabilidad de API bajo carga.

### Negativas
- Pérdida de hechos que antes se inferían (el sistema "aprende" más lento).
- Mayor rigidez en el routing (el usuario debe usar `/chat` para cambiar explícitamente).
```

**Paso 2: Commit**

```bash
git add adr/ADR-0024-reparacion-memoria-cognicion.md
git commit -m "docs(adr): ADR-0024 reparación memoria y cognición post-mortem v0.7.2"
```

---

## Tarea 1: Resiliencia JSON en Persistencia de Perfiles (Error A)

> Soluciona la "Amnesia" del sistema. Un solo carácter malformado en la DB no debe causar pérdida total del perfil.

**Archivos:**
- Crear: `src/memory/json_sanitizer.py` (utilidad compartida)
- Modificar: `src/memory/repositories/profile_repo.py:43-56`
- Modificar: `src/memory/knowledge_base.py:48-52`, `68-70`
- Test: `tests/unit/memory/test_json_sanitizer.py`

### Paso 1: Escribir el test que falla

```python
# tests/unit/memory/test_json_sanitizer.py
import pytest
from src.memory.json_sanitizer import safe_json_loads


class TestSafeJsonLoads:
    """Verifica que JSON malformado se repara antes de fallar."""

    def test_valid_json_passes(self):
        result = safe_json_loads('{"name": "Jhonn"}')
        assert result == {"name": "Jhonn"}

    def test_single_quotes_repaired(self):
        """Causa raíz del Error A: comillas simples en SQLite."""
        result = safe_json_loads("{'name': 'Jhonn', 'age': 30}")
        assert result == {"name": "Jhonn", "age": 30}

    def test_trailing_comma_repaired(self):
        result = safe_json_loads('{"name": "Jhonn", "age": 30,}')
        assert result == {"name": "Jhonn", "age": 30}

    def test_completely_invalid_returns_none(self):
        result = safe_json_loads("esto no es JSON de ningún tipo")
        assert result is None

    def test_empty_string_returns_none(self):
        result = safe_json_loads("")
        assert result is None

    def test_none_input_returns_none(self):
        result = safe_json_loads(None)
        assert result is None

    def test_nested_single_quotes_repaired(self):
        raw = "{'identity': {'name': 'Jhonn'}, 'values': ['honestidad']}"
        result = safe_json_loads(raw)
        assert result["identity"]["name"] == "Jhonn"
        assert "honestidad" in result["values"]
```

**Paso 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/memory/test_json_sanitizer.py -v
```
Esperado: FAIL con `ModuleNotFoundError: No module named 'src.memory.json_sanitizer'`

### Paso 3: Implementar `json_sanitizer.py`

```python
# src/memory/json_sanitizer.py
"""
Utilidad de sanitización JSON resiliente.

Repara errores comunes de formato antes de fallar:
comillas simples, comas finales, y otros artefactos
producidos por serialización incorrecta o LLMs.
"""

import ast
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def safe_json_loads(raw: str | None) -> dict[str, Any] | None:
    """
    Parsea JSON con múltiples estrategias de reparación.

    Intenta: json.loads → regex repair → ast.literal_eval.
    Retorna None solo si todas las estrategias fallan.
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Estrategia 1: JSON estándar
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Estrategia 2: Reparar comillas simples y comas finales
    repaired = _repair_json_string(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Estrategia 3: ast.literal_eval (para dicts de Python)
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    logger.error(
        f"JSON irrecuperable tras 3 estrategias. "
        f"Primeros 100 chars: {raw[:100]}"
    )
    return None


def _repair_json_string(raw: str) -> str:
    """Aplica reparaciones comunes al string JSON."""
    # Reemplazar comillas simples por dobles (fuera de strings)
    repaired = re.sub(r"(?<![\\])'", '"', raw)
    # Eliminar comas finales antes de } o ]
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired
```

**Paso 4: Ejecutar test para verificar que pasa**

```bash
pytest tests/unit/memory/test_json_sanitizer.py -v
```
Esperado: PASS (7/7 tests)

**Paso 5: Integrar en `profile_repo.py`**

Modificar `src/memory/repositories/profile_repo.py:43-56`. Reemplazar `json.loads(row["data"])` por `safe_json_loads(row["data"])`:

```python
# En profile_repo.py, línea 1-2, añadir import:
from src.memory.json_sanitizer import safe_json_loads

# Reemplazar el método load_profile (líneas 43-56):
async def load_profile(self, chat_id: str) -> dict | None:
    """Carga un perfil de usuario de la DB con reparación JSON."""
    db = await self.get_db()
    try:
        async with db.execute(
            "SELECT data FROM profiles WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                result = safe_json_loads(row["data"])
                if result is None:
                    logger.error(
                        f"Perfil corrupto irrecuperable para {chat_id}. "
                        f"Se retorna None para activar fallback a defaults."
                    )
                return result
            return None
    except Exception as e:
        logger.error(f"Error loading profile from SQLite: {e}")
        return None
```

**Paso 6: Integrar en `knowledge_base.py`**

Modificar `src/memory/knowledge_base.py:48-52` y `68-70`. Reemplazar `json.loads()` por `safe_json_loads()`:

```python
# En knowledge_base.py, añadir import:
from src.memory.json_sanitizer import safe_json_loads

# Línea 52: Reemplazar json.loads(raw_data) por:
parsed = safe_json_loads(raw_data)
if parsed:
    return parsed

# Línea 69: Reemplazar json.loads(results[0]["content"]) por:
kb_data = safe_json_loads(results[0]["content"])
if kb_data:
    return kb_data
```

**Paso 7: Commit**

```bash
git add src/memory/json_sanitizer.py src/memory/repositories/profile_repo.py \
  src/memory/knowledge_base.py tests/unit/memory/test_json_sanitizer.py
git commit -m "fix(memory): resiliencia JSON con sanitización multi-estrategia (Error A)"
```

---

## Tarea 2: Eliminar Inferencias del Extractor de Hechos (Error B)

> La causa directa de las alucinaciones persistentes. El sistema no debe "imaginar" hechos para la memoria.

**Archivos:**
- Modificar: `src/memory/fact_extractor.py:26-37` (prompt del sistema)
- Modificar: `src/agents/utils/knowledge_formatter.py:17-21` (filtro de procedencia)
- Test: `tests/unit/memory/test_fact_extractor.py` (actualizar)

### Paso 1: Escribir el test que falla

Añadir tests en `tests/unit/memory/test_fact_extractor.py`:

```python
# Añadir a tests/unit/memory/test_fact_extractor.py

class TestFactExtractorNoInference:
    """Verifica que el extractor RECHAZA hechos inferidos."""

    def test_merge_rejects_inferred_facts(self):
        """Hechos 'inferred' deben ser descartados en merge."""
        extractor = FactExtractor()
        old = {"entities": [], "preferences": [], "medical": [],
               "relationships": [], "milestones": [], "user_name": None}
        new = {
            "entities": [],
            "relationships": [
                {
                    "person": "ex-novia inventada",
                    "relation": "ex-pareja",
                    "attributes": {},
                    "source_type": "inferred",
                    "confidence": 0.6,
                    "evidence": "mencionó rancheras",
                    "sensitivity": "medium",
                },
                {
                    "person": "María",
                    "relation": "hermana",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 1.0,
                    "evidence": "mi hermana María",
                    "sensitivity": "low",
                },
            ],
            "preferences": [],
            "medical": [],
            "milestones": [],
        }
        merged = extractor._merge_knowledge(old, new)
        # Solo debe quedar el hecho explícito
        assert len(merged["relationships"]) == 1
        assert merged["relationships"][0]["person"] == "María"

    def test_merge_rejects_low_confidence(self):
        """Hechos con confianza < 0.8 deben ser descartados."""
        extractor = FactExtractor()
        old = {"entities": [], "preferences": [], "medical": [],
               "relationships": [], "milestones": [], "user_name": None}
        new = {
            "entities": [
                {
                    "name": "dato dudoso",
                    "type": "concepto",
                    "attributes": {},
                    "source_type": "explicit",
                    "confidence": 0.5,
                    "evidence": "algo vago",
                    "sensitivity": "low",
                },
            ],
            "preferences": [],
            "medical": [],
            "relationships": [],
            "milestones": [],
        }
        merged = extractor._merge_knowledge(old, new)
        assert len(merged["entities"]) == 0
```

**Paso 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/memory/test_fact_extractor.py::TestFactExtractorNoInference -v
```
Esperado: FAIL (los hechos inferidos se están aceptando actualmente)

### Paso 3: Modificar el prompt del extractor

En `src/memory/fact_extractor.py:26-37`, reemplazar las reglas del prompt:

```python
# Reemplazar las REGLAS (líneas 27-37) por:
"REGLAS:\\n"
"1. SOLO extrae hechos EXPLÍCITOS: datos que el usuario dijo literalmente.\\n"
"2. NO INFERIR: Si el usuario no lo dijo con sus palabras, NO lo extraigas. "
"No interpretes, no supongas, no deduzcas.\\n"
"3. source_type SIEMPRE debe ser 'explicit'. "
"Si no puedes clasificar un hecho como explícito, IGNÓRALO.\\n"
"4. CONFIANZA: Solo incluye hechos con confidence >= 0.8.\\n"
"5. EVIDENCIA: Incluye la cita textual EXACTA del usuario que soporta el hecho.\\n"
"6. SENSIBILIDAD: 'low' (gustos, datos demográficos), 'medium' (relaciones, trabajo), "
"'high' (salud mental, médico, trauma, emociones fuertes).\\n"
"7. NO DIAGNOSTIQUES. No afirmes rasgos de personalidad ni patrones cognitivos.\\n"
"8. PRECISIÓN: Si no hay una cita textual del usuario que confirme el hecho, "
"NO lo incluyas.\\n"
"9. Si el usuario menciona su nombre, extráelo en 'user_name'.\\n\\n"
```

### Paso 4: Añadir filtro en `_merge_knowledge`

En `src/memory/fact_extractor.py`, modificar `_merge_category` (línea 139-173) para filtrar antes de merge:

```python
def _merge_category(
    self, merged: dict[str, Any], new: dict[str, Any], key: str
) -> None:
    """Helper to merge a specific category of facts, filtering unsafe data."""
    if key not in merged:
        merged[key] = []

    # Index existing items by identity key
    existing: dict[str, int] = {
        self._identity_key(item, key): idx for idx, item in enumerate(merged[key])
    }

    for item in new.get(key, []):
        # FILTRO ANTI-ALUCINACIÓN: Rechazar inferidos y baja confianza
        if item.get("source_type") == "inferred":
            logger.info(
                f"Hecho inferido rechazado: {item.get('name', item.get('person', 'unknown'))}"
            )
            continue
        if item.get("confidence", 0) < 0.8:
            logger.info(
                f"Hecho de baja confianza rechazado ({item.get('confidence', 0):.1f}): "
                f"{item.get('name', item.get('person', 'unknown'))}"
            )
            continue

        ik = self._identity_key(item, key)
        if ik in existing:
            old_item = merged[key][existing[ik]]
            if isinstance(old_item.get("attributes"), dict) and isinstance(
                item.get("attributes"), dict
            ):
                old_item["attributes"].update(item["attributes"])

            if item.get("confidence", 0) >= old_item.get("confidence", 0):
                for field in (
                    "source_type", "confidence", "evidence", "sensitivity",
                ):
                    if field in item:
                        old_item[field] = item[field]
        else:
            merged[key].append(item)
            existing[ik] = len(merged[key]) - 1
```

**Paso 5: Ejecutar test para verificar que pasa**

```bash
pytest tests/unit/memory/test_fact_extractor.py -v
```
Esperado: PASS (todos los tests, incluidos los nuevos)

**Paso 6: Commit**

```bash
git add src/memory/fact_extractor.py tests/unit/memory/test_fact_extractor.py
git commit -m "fix(memory): eliminar inferencias del extractor de hechos (Error B)"
```

---

## Tarea 3: Filtro de Procedencia en Knowledge Formatter (Error B, capa 2)

> Defensa en profundidad: aunque un hecho inferido sobreviva en la DB (datos legacy), el formatter no lo mostrará al LLM sin marcarlo claramente.

**Archivos:**
- Modificar: `src/agents/utils/knowledge_formatter.py:4-53`
- Test: `tests/unit/test_knowledge_formatter.py` (crear)

### Paso 1: Escribir el test que falla

```python
# tests/unit/test_knowledge_formatter.py
from src.agents.utils.knowledge_formatter import format_knowledge_for_prompt


class TestKnowledgeFormatterProvenance:
    """Verifica que hechos inferidos se excluyen del prompt."""

    def test_explicit_facts_included(self):
        knowledge = {
            "entities": [
                {"name": "Python", "type": "lenguaje", "attributes": {},
                 "source_type": "explicit", "confidence": 1.0}
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "Python" in result

    def test_inferred_facts_excluded(self):
        """Hechos inferidos legacy NO deben llegar al prompt del LLM."""
        knowledge = {
            "relationships": [
                {"person": "ex-novia inventada", "relation": "ex-pareja",
                 "attributes": {}, "source_type": "inferred",
                 "confidence": 0.6}
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "ex-novia" not in result

    def test_low_confidence_explicit_excluded(self):
        knowledge = {
            "entities": [
                {"name": "dato dudoso", "type": "x", "attributes": {},
                 "source_type": "explicit", "confidence": 0.4}
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert "dato dudoso" not in result

    def test_empty_after_filter(self):
        knowledge = {
            "entities": [
                {"name": "x", "type": "y", "attributes": {},
                 "source_type": "inferred", "confidence": 0.3}
            ]
        }
        result = format_knowledge_for_prompt(knowledge)
        assert result == "No hay hechos confirmados aún."
```

**Paso 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/test_knowledge_formatter.py -v
```
Esperado: FAIL (`test_inferred_facts_excluded` falla porque actualmente se incluyen con tag)

### Paso 3: Modificar `knowledge_formatter.py`

Reemplazar el contenido de `src/agents/utils/knowledge_formatter.py`:

```python
from typing import Any

# Umbral mínimo de confianza para mostrar un hecho al LLM
MIN_CONFIDENCE_FOR_PROMPT = 0.7


def format_knowledge_for_prompt(knowledge: dict[str, Any]) -> str:
    """
    Formatea la Bóveda de Conocimiento excluyendo inferencias.
    Solo hechos explícitos con confianza >= 0.7 llegan al LLM.
    """
    sections = []

    def fmt_attrs(attrs: dict) -> str:
        if not attrs:
            return ""
        return ", ".join([f"{k}={v}" for k, v in attrs.items()])

    def is_trusted(item: dict) -> bool:
        """Filtro de procedencia: solo hechos explícitos y confiables."""
        if item.get("source_type") == "inferred":
            return False
        if item.get("confidence", 1.0) < MIN_CONFIDENCE_FOR_PROMPT:
            return False
        return True

    entities = [e for e in knowledge.get("entities", []) if is_trusted(e)]
    if entities:
        ents = "\n".join([
            f"- {e['name']} ({e['type']}): {fmt_attrs(e.get('attributes', {}))}"
            for e in entities
        ])
        sections.append(f"ENTIDADES:\n{ents}")

    medical = [m for m in knowledge.get("medical", []) if is_trusted(m)]
    if medical:
        meds = "\n".join([
            f"- {m['name']} ({m['type']}): {m.get('details', '')}"
            for m in medical
        ])
        sections.append(f"DATOS MÉDICOS:\n{meds}")

    relationships = [r for r in knowledge.get("relationships", []) if is_trusted(r)]
    if relationships:
        rels = "\n".join([
            f"- {r['person']} ({r['relation']}): {fmt_attrs(r.get('attributes', {}))}"
            for r in relationships
        ])
        sections.append(f"RELACIONES:\n{rels}")

    preferences = [p for p in knowledge.get("preferences", []) if is_trusted(p)]
    if preferences:
        prefs = "\n".join([
            f"- {p['category']}: {p['value']}"
            for p in preferences
        ])
        sections.append(f"PREFERENCIAS:\n{prefs}")

    return "\n\n".join(sections) if sections else "No hay hechos confirmados aún."
```

**Paso 4: Ejecutar tests**

```bash
pytest tests/unit/test_knowledge_formatter.py -v
```
Esperado: PASS (4/4)

**Paso 5: Commit**

```bash
git add src/agents/utils/knowledge_formatter.py tests/unit/test_knowledge_formatter.py
git commit -m "fix(memory): filtro de procedencia en knowledge formatter (Error B capa 2)"
```

---

## Tarea 4: Sesión Terapéutica Sticky en el Router (Error C)

> El Router debe reconocer que una queja del usuario durante una sesión CBT activa es "resistencia terapéutica", no un cambio de tema.

**Archivos:**
- Crear: `src/agents/orchestrator/routing/therapeutic_session.py` (nuevo módulo, ~35 LOC)
- Modificar: `src/agents/orchestrator/routing/enhanced_router.py:95-129`
- Modificar: `src/agents/orchestrator/routing/routing_prompts.py:33-46`
- Test: `tests/unit/test_therapeutic_session_stickiness.py` (crear)

### Paso 1: Escribir el test que falla

```python
# tests/unit/test_therapeutic_session_stickiness.py
import pytest
from unittest.mock import MagicMock
from src.agents.orchestrator.routing.enhanced_router import (
    EnhancedFunctionCallingRouter,
)
from src.agents.orchestrator.routing.therapeutic_session import (
    is_therapeutic_session_active,
    should_maintain_therapeutic_session,
)
from src.core.routing_models import IntentType, RoutingDecision


class TestTherapeuticStickiness:
    """Verifica que el router mantiene sesión CBT ante quejas."""

    def test_detects_active_therapeutic_session(self):
        """Si el último especialista fue CBT, la sesión terapéutica está activa."""
        state = {
            "event": MagicMock(event_type="text", content="no sirves"),
            "payload": {"last_specialist": "cbt_specialist"},
            "conversation_history": [],
        }
        assert is_therapeutic_session_active(state) is True

    def test_no_therapeutic_session_from_chat(self):
        state = {
            "event": MagicMock(event_type="text", content="hola"),
            "payload": {"last_specialist": "chat_specialist"},
            "conversation_history": [],
        }
        assert is_therapeutic_session_active(state) is False

    def test_complaint_during_cbt_stays_in_cbt(self):
        """Queja del usuario durante CBT = resistencia, no cambio de tema."""
        decision = RoutingDecision(
            intent=IntentType.CHAT,
            confidence=0.7,
            target_specialist="chat_specialist",
        )
        state = {
            "payload": {"last_specialist": "cbt_specialist"},
        }
        result = should_maintain_therapeutic_session(state, decision)
        assert result is True

    def test_explicit_topic_change_allowed(self):
        """Si el intent es TOPIC_SHIFT, sí se permite salir de CBT."""
        decision = RoutingDecision(
            intent=IntentType.TOPIC_SHIFT,
            confidence=0.9,
            target_specialist="chat_specialist",
        )
        state = {
            "payload": {"last_specialist": "cbt_specialist"},
        }
        result = should_maintain_therapeutic_session(state, decision)
        assert result is False
```

**Paso 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/test_therapeutic_session_stickiness.py -v
```
Esperado: FAIL (`ImportError: cannot import name 'is_therapeutic_session_active'`)

### Paso 3: Crear módulo `therapeutic_session.py`

Crear `src/agents/orchestrator/routing/therapeutic_session.py`:

```python
# src/agents/orchestrator/routing/therapeutic_session.py
"""
Detección y protección de sesiones terapéuticas activas (ADR-0024).

Evita que el Router cambie de especialista CBT durante una crisis
o resistencia terapéutica del usuario.
"""

import logging

from src.core.routing_models import IntentType, RoutingDecision
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Especialistas que activan modo terapéutico
THERAPEUTIC_SPECIALISTS = {"cbt_specialist"}

# Intents que rompen la sesión terapéutica explícitamente
SESSION_BREAKING_INTENTS = {IntentType.TOPIC_SHIFT}


def is_therapeutic_session_active(state: GraphStateV2) -> bool:
    """Verifica si la sesión actual es terapéutica."""
    last_specialist = state.get("payload", {}).get("last_specialist")
    return last_specialist in THERAPEUTIC_SPECIALISTS


def should_maintain_therapeutic_session(
    state: GraphStateV2, decision: RoutingDecision
) -> bool:
    """
    Determina si una decisión de routing debe ser anulada
    para mantener la continuidad de una sesión terapéutica.

    Retorna True si el router quiere cambiar FUERA de CBT
    pero la sesión terapéutica sigue activa y no hay un
    cambio de tema explícito.
    """
    if not is_therapeutic_session_active(state):
        return False

    # Si el router quiere mantener CBT, no hay conflicto
    if decision.target_specialist in THERAPEUTIC_SPECIALISTS:
        return False

    # Permitir salida solo con cambio de tema explícito o comando
    if decision.intent in SESSION_BREAKING_INTENTS:
        return False

    # Cualquier otro caso: mantener sesión terapéutica
    logger.info(
        f"Sesión terapéutica activa: anulando cambio a {decision.target_specialist}. "
        f"Intent '{decision.intent.value}' tratado como resistencia terapéutica."
    )
    return True
```

### Paso 4: Integrar en `enhanced_router.py`

Modificar `src/agents/orchestrator/routing/enhanced_router.py`. En los imports (línea 18-23), añadir:

```python
from .routing_utils import (
    detect_explicit_command,
    is_conversational_only,
    route_to_chat,
    update_state_with_decision,
)
from .therapeutic_session import should_maintain_therapeutic_session
```

En `_apply_routing_decision` (línea 95-129), añadir la verificación ANTES de la lógica de vulnerabilidad (después de la línea de stickiness, ~línea 114):

```python
    # ADR-0024: Protección de Sesión Terapéutica
    if should_maintain_therapeutic_session(state, decision):
        decision.target_specialist = "cbt_specialist"
        decision.next_actions = ["handle_resistance", "validate_frustration"]
        return self._route_to_specialist(state, decision)
```

### Paso 5: Actualizar prompt de routing

En `src/agents/orchestrator/routing/routing_prompts.py`, añadir después de la regla de STICKINESS (línea 46):

```
REGLA DE SESIÓN TERAPÉUTICA:
- Si el `Especialista previo` es `cbt_specialist` y el usuario expresa frustración, queja
  sobre el servicio, o respuestas cortas negativas (ej: "no sirves", "no me ayudas",
  "esto no funciona"), esto es RESISTENCIA TERAPÉUTICA, no un cambio de tema.
- En este caso, mantén `cbt_specialist` con intent `vulnerability` y añade la acción
  "handle_resistance" en next_actions.
- Solo cambia de CBT si el usuario dice explícitamente que quiere otro tema o usa un comando.
```

### Paso 6: Ejecutar tests

```bash
pytest tests/unit/test_therapeutic_session_stickiness.py -v
```
Esperado: PASS (4/4)

**Paso 7: Ejecutar tests de routing existentes para no-regresión**

```bash
pytest tests/unit/test_routing_intent_sync.py tests/integration/test_vulnerability_routing.py -v
```
Esperado: PASS

**Paso 8: Commit**

```bash
git add src/agents/orchestrator/routing/therapeutic_session.py \
  src/agents/orchestrator/routing/enhanced_router.py \
  src/agents/orchestrator/routing/routing_prompts.py \
  tests/unit/test_therapeutic_session_stickiness.py
git commit -m "fix(routing): sesión terapéutica sticky ante resistencia (Error C)"
```

---

## Tarea 5: Regulación de Tareas de Fondo (Error D)

> Las extracciones incrementales en segundo plano no deben saturar la cuota de API.

**Archivos:**
- Modificar: `src/memory/services/incremental_extractor.py:8-41`
- Modificar: `src/memory/long_term_memory.py` (si invoca extracción sin control)
- Test: `tests/unit/memory/test_incremental_extractor.py` (crear)

### Paso 1: Escribir el test que falla

```python
# tests/unit/memory/test_incremental_extractor.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.memory.services.incremental_extractor import (
    incremental_fact_extraction,
    _background_semaphore,
)


class TestIncrementalExtractorThrottle:
    """Verifica que la extracción incremental tiene límite de concurrencia."""

    def test_semaphore_exists(self):
        """Debe existir un semáforo global para limitar concurrencia."""
        assert _background_semaphore is not None
        # Máximo 1 extracción simultánea
        assert _background_semaphore._value == 1

    @pytest.mark.asyncio
    async def test_skips_when_semaphore_busy(self):
        """Si ya hay una extracción en curso, la nueva se descarta."""
        # Adquirir el semáforo para simular tarea en curso
        await _background_semaphore.acquire()
        try:
            buffer = AsyncMock()
            buffer.get_messages.return_value = [
                {"role": "user", "content": "test"}
            ]
            # Esta llamada debe ser descartada (no-op)
            with patch(
                "src.memory.services.incremental_extractor.fact_extractor"
            ) as mock_fe:
                await incremental_fact_extraction("test_chat", buffer)
                mock_fe.extract_facts.assert_not_called()
        finally:
            _background_semaphore.release()
```

**Paso 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/memory/test_incremental_extractor.py -v
```
Esperado: FAIL (`ImportError: cannot import name '_background_semaphore'`)

### Paso 3: Modificar `incremental_extractor.py`

Reemplazar contenido de `src/memory/services/incremental_extractor.py`:

```python
import asyncio
import logging

from src.memory.redis_buffer import RedisMessageBuffer

logger = logging.getLogger(__name__)

# ADR-0024: Semáforo global para limitar extracción concurrente (máx 1)
_background_semaphore = asyncio.Semaphore(1)


async def incremental_fact_extraction(
    chat_id: str, buffer: RedisMessageBuffer
) -> None:
    """
    Realiza una extracción de hechos parcial sin limpiar el buffer.
    Protegida por semáforo para evitar saturación de API.
    """
    # Si ya hay una extracción en curso, descartar esta
    if _background_semaphore.locked():
        logger.debug(
            f"Extracción incremental descartada para {chat_id}: "
            f"otra extracción en curso."
        )
        return

    async with _background_semaphore:
        try:
            from src.memory.fact_extractor import fact_extractor
            from src.memory.knowledge_base import knowledge_base_manager

            raw_buffer = await buffer.get_messages(chat_id)
            if not raw_buffer:
                return

            recent_msgs = raw_buffer[-10:]
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}" for m in recent_msgs
            ])

            current_knowledge = await knowledge_base_manager.load_knowledge(
                chat_id
            )
            updated_knowledge = await fact_extractor.extract_facts(
                conversation_text, current_knowledge
            )
            await knowledge_base_manager.save_knowledge(
                chat_id, updated_knowledge
            )
            logger.info(
                f"Incremental fact extraction complete for {chat_id}"
            )

        except Exception as e:
            logger.error(
                f"Error in incremental fact extraction for {chat_id}: {e}"
            )
```

**Paso 4: Ejecutar test para verificar que pasa**

```bash
pytest tests/unit/memory/test_incremental_extractor.py -v
```
Esperado: PASS (2/2)

**Paso 5: Commit**

```bash
git add src/memory/services/incremental_extractor.py \
  tests/unit/memory/test_incremental_extractor.py
git commit -m "fix(memory): semáforo de concurrencia en extracción incremental (Error D)"
```

---

## Tarea 6: Verificación Integral

> Ejecutar la suite completa de tests y `make verify` para confirmar que no hay regresiones.

**Archivos:** Ninguno (solo ejecución)

### Paso 1: Ejecutar todos los tests unitarios nuevos

```bash
pytest tests/unit/memory/test_json_sanitizer.py \
  tests/unit/memory/test_fact_extractor.py \
  tests/unit/test_knowledge_formatter.py \
  tests/unit/test_therapeutic_session_stickiness.py \
  tests/unit/memory/test_incremental_extractor.py -v
```
Esperado: PASS (todos)

### Paso 2: Ejecutar suite completa

```bash
make verify
```
Esperado: PASS (lint + test + arquitectura)

### Paso 3: Verificar límites de LOC de archivos modificados

Archivos a verificar (máximo 200 LOC para lógica):
- `src/memory/json_sanitizer.py` - ~55 LOC (OK)
- `src/memory/fact_extractor.py` - ~178 LOC (OK, dentro de límite)
- `src/agents/utils/knowledge_formatter.py` - ~60 LOC (OK)
- `src/agents/orchestrator/routing/enhanced_router.py` - ~190 LOC (OK)
- `src/agents/orchestrator/routing/routing_utils.py` - ~250 LOC (**ATENCIÓN**: verificar si excede 200. Si es así, extraer funciones terapéuticas a un archivo separado como `therapeutic_session.py`)
- `src/memory/services/incremental_extractor.py` - ~55 LOC (OK)

### Paso 4: Commit final y tag de versión

```bash
git add -A
git commit -m "feat(v0.8.1): reparación memoria y cognición - cierre de post-mortem v0.7.2"
```

---

## Resumen de Cambios por Archivo

| Archivo | Acción | Tarea | Error |
|---------|--------|-------|-------|
| `adr/ADR-0024-reparacion-memoria-cognicion.md` | Crear | 0 | Todos |
| `src/memory/json_sanitizer.py` | Crear | 1 | A |
| `src/memory/repositories/profile_repo.py` | Modificar | 1 | A |
| `src/memory/knowledge_base.py` | Modificar | 1 | A |
| `src/memory/fact_extractor.py` | Modificar | 2 | B |
| `src/agents/utils/knowledge_formatter.py` | Modificar | 3 | B |
| `src/agents/orchestrator/routing/enhanced_router.py` | Modificar | 4 | C |
| `src/agents/orchestrator/routing/routing_prompts.py` | Modificar | 4 | C |
| `src/agents/orchestrator/routing/routing_utils.py` | Modificar | 4 | C |
| `src/memory/services/incremental_extractor.py` | Modificar | 5 | D |
| Tests nuevos (5 archivos) | Crear | 1-5 | Todos |

**Total: 6 archivos nuevos, 6 archivos modificados, 6 commits atómicos.**

---
*Plan generado a partir del informe forense `v0.7.2-analisis-forense-alucinaciones.md`. Aprobación del usuario requerida antes de ejecutar.*
