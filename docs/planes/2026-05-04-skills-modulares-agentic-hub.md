# PLAN: Sistema de Skills Modulares y Agentic Hub (ADR-0026)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Completado
- **Fecha:** 2026-05-12
- **Razón de Creación:** Nueva Funcionalidad + Refactorización
- **ADR Relacionado:** `adr/ADR-0026-skills-modulares-agentic-hub.md`
- **Alineación Plan Maestro:** Bloque C.1 (Fábrica de Habilidades) + parcialmente C.2 (Integración de Herramientas)
- **Objetivo General:** Transformar AEGEN en un sistema de IA autónomo, profesional, con memoria persistente y capacidades de acción externa.

---

## Resumen Ejecutivo

**Problema:** La arquitectura actual separa "skills" (overlays Markdown en `src/personality/skills/`) de "especialistas" (clases Python en `src/agents/specialists/`). Añadir un nuevo agente requiere modificar ≥6 archivos (`registry.py`, `__init__.py`, `specialist_file.py`, `tool_file.py`, `routing_prompts.py`, `intent_patterns_data.py`), con alto riesgo de error y fricción.

**Por qué existe:** Evolución orgánica. Los overlays nacieron como modificadores de prompt; los especialistas como agentes LangGraph. Nunca se unificaron.

**Solución estructural:** Fusionar ambos conceptos en un "Skill como Directorio" auto-descriptivo (`SKILL.md` con YAML frontmatter + `tools.py` + `schemas.py`). Un `SkillLoader` descubre skills del filesystem y un `SkillBasedSpecialist` genérico reemplaza las clases hardcoded. El ADR también define 4 elementos adicionales: memoria híbrida FTS5, learning loop, gateway unificado y automatizaciones programadas.

**Impacto si NO se hace:** Cada nuevo agente (psicotrading, investigación, quant) requerirá ~2h de boilerplate y riesgo de regresión en el pipeline existente. La escalabilidad del Bloque C del Plan Maestro queda bloqueada.

---

## Análisis de Impacto

### Dependencias afectadas

**Módulos que importan desde `src.agents.specialists` (4 imports):**

| Consumidor | Import | Acción requerida |
|---|---|---|
| `src/main.py:46` | `register_all_specialists` | Reemplazar por `register_all_skills` |
| `src/agents/specialists/chat_agent.py:13` | `chat.chat_tool` | Se mueve a `src/personality/skills/chat/tools.py` |
| `src/agents/specialists/cbt_specialist.py:7` | `cbt.cbt_tool` | Se mueve a `src/personality/skills/tcc/tools.py` |
| `tests/unit/test_cbt_safety.py:3` | `cbt.prompt_builder` | Actualizar import |

**Módulos que importan desde `src.personality` (5 imports externos):**

| Consumidor | Import | Acción requerida |
|---|---|---|
| `src/agents/specialists/chat/chat_tool.py:19` | `system_prompt_builder` | Se mueve al skill; import se actualiza |
| `src/agents/specialists/cbt/cbt_tool.py:18` | `system_prompt_builder` | Se mueve al skill; import se actualiza |
| `tests/unit/personality/test_prompt_renders.py` | `render_dialect_rules, render_style_adaptation` | No cambia (funciones se mantienen) |
| `tests/unit/personality/test_overhaul_integration.py` | `system_prompt_builder` | Import se actualiza |

**Interfaces afectadas:**
- `src/core/interfaces/specialist.py` (`SpecialistInterface`): Se mantiene pero se implementa genéricamente por `SkillBasedSpecialist`.
- `src/core/registry.py` (`SpecialistRegistry` + `Specialist` Protocol): Se extiende para soportar registro dinámico desde filesystem.

**Schemas afectados:**
- `src/core/schemas/agents.py`: Se añade `SkillManifest` model.
- `src/personality/types.py`: `SkillOverlay` se extiende o reemplaza por `SkillContent`.

### Cobertura de tests existente

| Código afectado | Tests existentes | Acción |
|---|---|---|
| `PersonalityLoader` | `test_overhaul_integration.py` (indirecto) | Crear tests directos ANTES de refactorizar |
| `PersonalityManager` | Ninguno | Crear tests ANTES de refactorizar |
| `SpecialistRegistry` | Ninguno | Crear tests ANTES de refactorizar |
| `register_all_specialists()` | Ninguno | Crear tests ANTES de refactorizar |
| `SystemPromptBuilder.build()` | `test_overhaul_integration.py` (3 tests) | Mantener, adaptar imports |
| `prompt_renders` | `test_prompt_renders.py` (8 tests) | No cambia |
| Specialist classes (CBT, Chat, Transcription) | Ninguno directo | Crear tests de migración |
| CBT prompt_builder | `test_cbt_safety.py` | Actualizar import |

### Verificación del pipeline

El cambio toca `src/agents/` y potencialmente `src/api/`. Flujo completo a verificar:

```
Telegram → Webhook → TelegramAdapter → CanonicalEventV1
  → MasterOrchestrator → EnhancedRouter → [SkillBasedSpecialist]
  → Graph Execution → Redis Buffer → SQLite
  → Respuesta → Telegram
```

Puntos críticos:
1. `OrchestratorFactory.create_orchestrator()` debe funcionar con skills dinámicos.
2. `OptimizedSpecialistCache.initialize_cache()` debe cargar tools de skills dinámicos.
3. `EnhancedFunctionCallingRouter` debe incluir skills dinámicos en su prompt de routing.
4. `OrchestratorGraphBuilder.build()` debe crear nodos para skills dinámicos.

---

## Fase 1: Fundaciones — SkillManifest y Parser YAML

### Objetivo
Crear el modelo de datos (`SkillManifest`) y el parser de `SKILL.md` (YAML frontmatter + Markdown body) con tests completos. No se modifica ningún código existente.

### Justificación
Todo el sistema se construye sobre la capacidad de parsear `SKILL.md`. Sin esto, nada más funciona.

### Task 1.1: Modelo SkillManifest

**Files:**
- Create: `src/core/schemas/skills.py`
- Test: `tests/unit/core/test_skill_manifest.py`

**Step 1: Write failing test**

```python
# tests/unit/core/test_skill_manifest.py
from src.core.schemas.skills import SkillManifest, SkillRequirements, SkillContent

def test_skill_manifest_minimal():
    m = SkillManifest(name="Test", id="test_skill", version="1.0.0", capabilities=["text"])
    assert m.name == "Test"
    assert m.requirements.memory_access == "full"  # default
    assert m.requirements.priority == 5  # default
    assert m.requirements.update_history is True  # default
    assert m.requirements.chain_to is None  # default
    assert m.async_capable is False  # default

def test_skill_manifest_full():
    m = SkillManifest(
        name="CBT Specialist", id="cbt_therapeutic", version="1.0.0",
        capabilities=["psicologia", "tcc", "apoyo_emocional"],
        requirements=SkillRequirements(
            tools=["cbt_therapeutic_guidance_tool"],
            memory_access="full", priority=10,
            update_history=False, chain_to=None,
        ),
        async_capable=False,
    )
    assert m.requirements.priority == 10
    assert "tcc" in m.capabilities

def test_skill_manifest_rejects_empty_id():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SkillManifest(name="X", id="", version="1.0.0", capabilities=[])

def test_skill_content_with_sections():
    sc = SkillContent(
        manifest=SkillManifest(name="T", id="t", version="1.0.0", capabilities=[]),
        tone_modifiers="Directo, eficiente",
        instructions="Responde conciso",
        anti_patterns="No uses jerga",
        linguistic_rules="Eco léxico activo",
    )
    assert sc.tone_modifiers == "Directo, eficiente"
    assert sc.linguistic_rules == "Eco léxico activo"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/core/test_skill_manifest.py -v`

**Step 3: Write minimal implementation**

```python
# src/core/schemas/skills.py
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict

class SkillRequirements(BaseModel):
    tools: List[str] = Field(default_factory=list)
    memory_access: str = "full"
    priority: int = Field(default=5, ge=0, le=100)
    update_history: bool = True
    chain_to: Optional[str] = None

class SkillSchedule(BaseModel):
    cron: str
    description: str = ""
    enabled: bool = True

class SkillManifest(BaseModel):
    name: str
    id: str
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    requirements: SkillRequirements = Field(default_factory=SkillRequirements)
    async_capable: bool = False
    schedule: Optional[SkillSchedule] = None

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("skill id cannot be empty")
        return v.strip()

class SkillContent(BaseModel):
    manifest: SkillManifest
    tone_modifiers: str = ""
    instructions: str = ""
    anti_patterns: str = ""
    linguistic_rules: str = ""
    raw_sections: Dict[str, str] = Field(default_factory=dict)
```

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/core/test_skill_manifest.py -v`

**Step 5: Commit**

### Task 1.2: Parser de SKILL.md

**Files:**
- Create: `src/personality/skill_parser.py`
- Test: `tests/unit/personality/test_skill_parser.py`

**Step 1: Write failing test**

```python
# tests/unit/personality/test_skill_parser.py
import pytest
from src.personality.skill_parser import parse_skill_md

VALID_SKILL_MD = """---
name: "CBT Specialist"
id: "cbt_therapeutic"
version: "1.0.0"
capabilities: ["psicologia", "tcc"]
requirements:
  tools: ["cbt_therapeutic_guidance_tool"]
  memory_access: "full"
  priority: 10
---
## Tone Modifiers
Empático analítico. Firmeza profesional.

## Instructions
Detecta distorsiones cognitivas.
Reestructuración agresiva.

## Anti-Patterns Específicos
No uses tono maternal.

## Reglas Lingüísticas del Skill
Firmeza benevolente.
"""

def test_parse_valid_skill_md():
    result = parse_skill_md(VALID_SKILL_MD)
    assert result.manifest.name == "CBT Specialist"
    assert result.manifest.id == "cbt_therapeutic"
    assert result.manifest.requirements.priority == 10
    assert "Empático" in result.tone_modifiers
    assert "distorsiones" in result.instructions
    assert "maternal" in result.anti_patterns
    assert "Firmeza benevolente" in result.linguistic_rules

def test_parse_missing_frontmatter():
    result = parse_skill_md("## Instructions\nHaz cosas.")
    assert result.manifest.id == "unknown"
    assert "Haz cosas" in result.instructions

def test_parse_empty_content():
    result = parse_skill_md("")
    assert result.manifest.id == "unknown"

def test_parse_invalid_yaml_graceful():
    content = "---\n[invalid yaml: {{\n---\n## Instructions\nFallback."
    result = parse_skill_md(content)
    assert result.manifest.id == "unknown"
    assert "Fallback" in result.instructions

def test_parse_extra_sections_preserved():
    content = "---\nname: X\nid: x\n---\n## Custom Section\nDatos custom."
    result = parse_skill_md(content)
    assert "Custom Section" in result.raw_sections
    assert "Datos custom" in result.raw_sections["Custom Section"]
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/personality/test_skill_parser.py -v`

**Step 3: Write minimal implementation**

```python
# src/personality/skill_parser.py
from __future__ import annotations
import logging
import re
import yaml
from typing import Any, Dict
from src.core.schemas.skills import SkillContent, SkillManifest

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_SECTION_RE = re.compile(r"^## (.+?)$\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)

_SECTION_MAP = {
    "tone modifiers": "tone_modifiers",
    "instructions": "instructions",
    "anti-patterns": "anti_patterns",
    "anti-patterns específicos": "anti_patterns",
    "reglas lingüísticas del skill": "linguistic_rules",
    "reglas linguisticas del skill": "linguistic_rules",
}

def parse_skill_md(content: str) -> SkillContent:
    manifest = _parse_frontmatter(content)
    sections = _parse_sections(content)

    known: Dict[str, str] = {}
    raw: Dict[str, str] = {}
    for heading, body in sections.items():
        key = _SECTION_MAP.get(heading.lower().strip())
        if key:
            known[key] = body.strip()
        else:
            raw[heading] = body.strip()

    return SkillContent(manifest=manifest, raw_sections=raw, **known)

def _parse_frontmatter(content: str) -> SkillManifest:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return SkillManifest(name="Unknown", id="unknown")
    try:
        data = yaml.safe_load(match.group(1)) or {}
        return SkillManifest(**data)
    except Exception:
        logger.warning("Invalid YAML frontmatter in SKILL.md, using defaults")
        return SkillManifest(name="Unknown", id="unknown")

def _parse_sections(content: str) -> Dict[str, str]:
    body = _FRONTMATTER_RE.sub("", content)
    return {m.group(1): m.group(2) for m in _SECTION_RE.finditer(body)}
```

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/personality/test_skill_parser.py -v`

**Step 5: Commit**

### Task 1.3: Actualizar exports de schemas

**Files:**
- Modify: `src/core/schemas/__init__.py`

**Step 1:** Añadir `from src.core.schemas.skills import SkillManifest, SkillContent, SkillRequirements, SkillSchedule` y exportarlos en `__all__`.

**Step 2:** Run: `make verify`

**Step 3:** Commit

---

## Fase 2: Migración de Estructura de Directorios

### Objetivo
Convertir los overlays actuales (`*_overlay.md`) al formato `SKILL.md` con YAML frontmatter, dentro de directorios individuales. Actualizar `PersonalityLoader` para leer el nuevo formato manteniendo retrocompatibilidad.

### Task 2.1: Migrar Chat a SKILL.md

**Files:**
- Create: `src/personality/skills/chat/SKILL.md`
- Read: `src/personality/skills/chat_overlay.md`

**Action:** Crear directorio `src/personality/skills/chat/`. Escribir `SKILL.md` con YAML frontmatter (id: chat_specialist, tools: [conversational_chat_tool]) + contenido de `chat_overlay.md`.

### Task 2.2: Migrar TCC a SKILL.md

**Files:**
- Create: `src/personality/skills/tcc/SKILL.md`
- Read: `src/personality/skills/tcc_overlay.md`

**Action:** Crear directorio `src/personality/skills/tcc/`. Escribir `SKILL.md` con YAML frontmatter (id: cbt_specialist, tools: [cbt_therapeutic_guidance_tool]) + contenido de `tcc_overlay.md`.

### Task 2.3: Crear SKILL.md para Transcription

**Files:**
- Create: `src/personality/skills/transcription/SKILL.md`

**Action:** Crear directorio `src/personality/skills/transcription/`. Escribir `SKILL.md` con manifest (id: transcription_agent, chain_to: chat_specialist).

### Task 2.4: Refactorizar PersonalityLoader

**Files:**
- Modify: `src/personality/loader.py`

**Action:** Modificar `load_skill_overlay(name)` para que busque `skills/{name}/SKILL.md` primero. Si existe, usar `parse_skill_md`. Si no, fallback a `{name}_overlay.md`.

### Task 2.5: Refactorizar PersonalityManager

**Files:**
- Modify: `src/personality/manager.py`

**Action:** Cambiar caché de `_overlays` para que almacene objetos `SkillContent`. Eliminar logger duplicado. Corregir `__new__` para inyección de `PersonalityLoader`.

### Task 2.6: Adaptar SystemPromptBuilder

**Files:**
- Modify: `src/personality/prompt_builder.py`

**Action:** Actualizar `_build_skill_section` para aceptar `SkillContent`. Incluir la nueva sección `linguistic_rules` en el prompt.

### Task 2.7: Limpieza y Tests

**Files:**
- Delete: `src/personality/skills/chat_overlay.md`
- Delete: `src/personality/skills/tcc_overlay.md`
- Test: `tests/unit/personality/test_loader.py`

---

## Fase 3: Cargador Dinámico y SkillBasedSpecialist

### Objetivo
Crear el `SkillLoader` que descubre skills del filesystem y el `SkillBasedSpecialist` genérico.

### Task 3.1: Implementar SkillLoader

**Files:**
- Create: `src/personality/skill_loader.py`

**Action:** Crear clase que escanee `src/personality/skills/` y `storage/skills/` buscando `SKILL.md`. Usar `importlib.util` para cargar `tools.py` opcionalmente.

### Task 3.2: Implementar SkillBasedSpecialist

**Files:**
- Create: `src/agents/specialists/skill_based_specialist.py`

**Action:** Crear clase genérica que implemente `SpecialistInterface`. El grafo tendrá un solo nodo que ejecute el tool definido en el manifest.

### Task 3.3: Refactorizar SpecialistRegistry

**Files:**
- Modify: `src/core/registry.py`

**Action:** Añadir `register_from_skills(skills_list)`. Eliminar Protocol `Specialist` duplicado (usar el ABC).

### Task 3.4: Actualizar registro al inicio

**Files:**
- Modify: `src/agents/specialists/__init__.py`

**Action:** Cambiar `register_all_specialists` para que use `SkillLoader` y registre todo dinámicamente.

---

## Fase 4: Migración Completa + Skill Psicotrading

### Objetivo
Mover código de especialistas a carpetas de skills y añadir un nuevo skill de prueba.

### Task 4.1: Mover lógica de CBT al skill tcc

**Action:** Mover `src/agents/specialists/cbt/cbt_tool.py` → `src/personality/skills/tcc/tools.py`. Actualizar imports.

### Task 4.2: Mover lógica de Chat al skill chat

**Action:** Mover `src/agents/specialists/chat/chat_tool.py` → `src/personality/skills/chat/tools.py`. Actualizar imports.

### Task 4.3: Eliminar clases especialistas legacy

**Action:** Borrar `cbt_specialist.py`, `chat_agent.py`, `transcription_agent.py`. Verificar que `make verify` pasa.

### Task 4.4: Crear Skill Psicotrading

**Files:**
- Create: `src/personality/skills/psicotrading/SKILL.md`
- Create: `src/personality/skills/psicotrading/tools.py`

**Action:** Implementar un coach de trading básico para validar que el sistema lo detecta y lo integra en el router automáticamente.

---

## Fase 5: Operaciones Asíncronas y Delegación

### Objetivo
Habilitar workers para tareas de larga duración.

### Task 5.1: Worker Infrastructure

**Files:**
- Create: `src/core/interfaces/worker.py`
- Create: `src/agents/workers/worker_manager.py`

**Action:** Implementar el gestor de tareas en segundo plano que publica resultados en el `RedisEventBus`.

### Task 5.2: Async Skills

**Action:** Modificar `SkillBasedSpecialist` para que, si el manifest marca `async_capable: true`, delegue al `WorkerManager` y responda un ack inmediato al usuario.

---

## Fase 6: Memoria Híbrida FTS5 Mejorada

### Objetivo
Refinar la búsqueda por palabras clave filtrada por skill.

### Task 6.1: Contextual Keyword Search

**Files:**
- Modify: `src/memory/keyword_search.py`
- Modify: `src/memory/schema.sql`

**Action:** Añadir columna `source_skill` a memorias. Permitir filtrar FTS5 por este campo.

---

## Fase 7: Learning Loop — Autoinstalación de Skills

### Objetivo
Generar skills automáticamente desde el historial.

### Task 7.1: SkillGenerator Agent

**Files:**
- Create: `src/personality/skill_generator.py`

**Action:** Crear agente que analice conversaciones en `consolidation_worker.py` y cree `SKILL.md` en `storage/skills/` si detecta un dominio nuevo repetido.

---

## Fase 8: Gateway Protocol Unificado

### Objetivo
Abstraer el transporte (Telegram, WebSocket).

### Task 8.1: Channel Interface

**Files:**
- Create: `src/core/interfaces/channel.py`
- Create: `src/api/adapters/websocket_adapter.py`

---

## Fase 9: Automatizaciones Programadas (CronScheduler)

### Objetivo
Soportar tareas recurrentes en skills.

### Task 9.1: CronScheduler Integration

**Files:**
- Create: `src/agents/scheduler/cron_scheduler.py`

**Action:** Usar `croniter` para ejecutar el tool del skill según el campo `schedule` del manifest.

---

## Seguimiento de Tareas

- [x] Fase 1: Fundaciones
- [x] Fase 2: Estructura de Directorios
- [x] Fase 3: Cargador Dinámico
- [x] Fase 4: Migración Completa + Psicotrading
- [x] Fase 5: Async Workers
- [x] Fase 6: Memoria Híbrida
- [x] Fase 7: Learning Loop
- [x] Fase 8: Gateway Protocol
- [x] Fase 9: CronScheduler
- [ ] Fase 3: Cargador Dinámico
- [ ] Fase 4: Migración Completa + Psicotrading
- [ ] Fase 5: Async Workers
- [ ] Fase 6: Memoria Híbrida
- [ ] Fase 7: Learning Loop
- [ ] Fase 8: Gateway Protocol
- [ ] Fase 9: CronScheduler

---

## Notas y Riesgos

- **Riesgo:** Inyección de código en `tools.py` dinámicos. Mitigación: solo cargar de `src/` por defecto; `storage/` restringido a solo MD inicialmente.
- **Riesgo:** Romper el routing. Mitigación: tests de integración del router obligatorios en cada fase.
