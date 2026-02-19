# Plan: Solución Integral para Import Chain Failure + Desacoplamiento Estructural de Arranque

### Diagnóstico Confirmado

**Problema Inmediato:** `src/personality/prompt_renders.py` nunca fue commiteado. El commit `c7047d9` extrajo dos métodos de `SystemPromptBuilder` (`_render_dialect_rules` y `_render_style_adaptation`) y los reemplazó por imports a un módulo que no existe.

**Problema Estructural (la causa real de la fragilidad):** La cadena de imports eager en el arranque hace que CUALQUIER error en CUALQUIER especialista o sus dependencias transitivas mate toda la aplicación:

```
main.py (top-level, línea 101)
  → webhooks.py → telegram_adapter.py → debounce_manager.py → event_processor.py
    → src.agents.orchestrator.factory
      → Python carga src/agents/__init__.py (eager: from . import specialists)
        → src/agents/specialists/__init__.py (eager: from . import cbt_specialist, chat_agent, ...)
          → chat_tool.py → prompt_builder.py → prompt_renders.py  ← NO EXISTE
```

Un solo archivo faltante en `src/personality/` destruye la cadena entera. Esto no es un accidente aislado - es un defecto arquitectural que hará que cualquier futuro error de import en un especialista tenga el mismo efecto catastrófico.

---

### Fase 1: Crear el módulo faltante `prompt_renders.py`

**Objetivo:** Restaurar la funcionalidad rota con el código exacto que fue eliminado del commit `c7047d9`.

**Archivo:** `src/personality/prompt_renders.py`

**Contenido:** Dos funciones puras (sin estado, sin side effects) recuperadas verbatim del diff de git:

| Función | Firma | Líneas originales |
|---|---|---|
| `render_dialect_rules` | `(linguistic: LinguisticProfile) -> str` | Lógica de prioridad: Preferencia > Confirmación > Neutro |
| `render_style_adaptation` | `(style: StyleSignals \| None) -> str` | Adaptación por formalidad, brevedad, uso de emoji |

**Imports necesarios:**
- `from src.personality.types import LinguisticProfile, StyleSignals`

**Validación:** Estos son los 2 únicos símbolos importados por `prompt_builder.py:9-12`. Las firmas coinciden exactamente con las llamadas en líneas 107 y 110.

---

### Fase 2: Romper la cadena de imports eager (cambio estructural)

**Objetivo:** Que un error en un especialista individual NUNCA bloquee el arranque de FastAPI.

**Patrón elegido:** Lifespan-deferred registration (Pattern B del análisis). Es el patrón ya probado en `main.py:30-51` para `global_knowledge_loader` y `KnowledgeWatcher`.

#### 2.1 — Modificar `src/agents/specialists/__init__.py`

**Estado actual (línea 6):**
```python
from . import cbt_specialist, chat_agent, transcription_agent  # EAGER — ejecuta registro al importar
```

**Estado propuesto:**
```python
# NO import eager de módulos especialistas
import logging

logger = logging.getLogger(__name__)

def register_all_specialists() -> None:
    """Registra todos los especialistas. Llamado desde lifespan(), no al importar."""
    specialist_modules = [
        ("cbt_specialist", "cbt_specialist"),
        ("chat_agent", "chat_agent"),
        ("transcription_agent", "transcription_agent"),
    ]
    for module_name, display_name in specialist_modules:
        try:
            __import__(f"src.agents.specialists.{module_name}")
            logger.info("Especialista '%s' registrado exitosamente", display_name)
        except Exception:
            logger.exception("Error registrando especialista '%s' — degradación suave", display_name)
```

**Beneficios:**
- Importar `src.agents` ya no desencadena la cadena.
- Si un especialista falla, los demás siguen funcionando (graceful degradation).
- El logging da visibilidad exacta de qué especialista falló.

#### 2.2 — Modificar `src/agents/__init__.py`

**Estado actual (línea 5):**
```python
from . import specialists  # EAGER — desencadena toda la cascada
```

**Estado propuesto:**
```python
# Package marker — specialist registration is deferred to lifespan
```

Eliminamos el import eager. El paquete `src.agents` se convierte en un namespace package limpio.

#### 2.3 — Modificar `src/main.py` (función `lifespan`)

Añadir la llamada a `register_all_specialists()` dentro de la función `lifespan`, **antes** de que se inicialicen los recursos globales que dependen del registry (o justo después, según el orden de dependencias). El patrón ya existe en las líneas 30-51:

```python
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... imports diferidos existentes ...
    from src.agents.specialists import register_all_specialists
    register_all_specialists()
    # ... resto del lifespan ...
```

**Nota:** La función `register_all_specialists()` es síncrona porque `specialist_registry.register()` es síncrono, y los module-level side effects de cada especialista son síncronos.

#### 2.4 — Validar que el `LazyMasterOrchestrator` sigue funcionando

El `LazyMasterOrchestrator` en `factory.py:129-176` llama a `specialist_registry.get_all_specialists()` cuando se invoca por primera vez. Esto ocurre en la primera request HTTP — **después** de que `lifespan()` haya completado el registro. El flujo temporal es:

```
1. FastAPI startup → lifespan() ejecuta → register_all_specialists() llena el registry
2. Primera request → LazyMasterOrchestrator._get_instance() → usa el registry ya poblado
```

No se requieren cambios en `factory.py`.

---

### Fase 3: Tests unitarios para `prompt_renders.py`

**Objetivo:** Cubrir las funciones extraídas con tests que validen todas las ramas lógicas.

**Archivo:** `tests/unit/personality/test_prompt_renders.py`

**Tests planificados:**

| Test | Qué valida |
|---|---|
| `test_render_dialect_preferred_wins` | Preferencia explícita tiene prioridad máxima |
| `test_render_dialect_confirmed_location` | Ubicación confirmada genera sugerencia suave |
| `test_render_dialect_neutral_default` | Sin datos → neutralidad cálida + eco léxico |
| `test_render_style_adaptation_none` | `style=None` → string vacío |
| `test_render_style_muy_formal` | Formality "muy_formal" → elimina coloquialismos |
| `test_render_style_casual` | Formality "casual" → cercano y relajado |
| `test_render_style_telegraphic` | Brevity "telegráfico" → ultra-conciso |
| `test_render_style_no_emoji` | `uses_emoji=False` → reduce emojis |

Estos tests son puros (sin mocks, sin I/O, sin async) porque las funciones son puras.

**Archivo existente a verificar:** `tests/unit/personality/test_overhaul_integration.py` — este test importa `system_prompt_builder` que a su vez importa `prompt_renders`. Actualmente está roto por la misma cadena. Con la Fase 1 completada, debería volver a pasar sin cambios.

---

### Fase 4: Verificación integral

| Paso | Comando | Qué valida |
|---|---|---|
| 1 | `python -c "from src.personality.prompt_renders import render_dialect_rules, render_style_adaptation"` | El módulo es importable |
| 2 | `python -c "from src.personality.prompt_builder import system_prompt_builder"` | La cadena de imports funciona |
| 3 | `python -c "from src.agents.specialists import register_all_specialists; register_all_specialists()"` | Registro diferido funciona |
| 4 | `make test` | Tests pasan (incluyendo los nuevos y el existente `test_overhaul_integration.py`) |
| 5 | `make lint` | Ruff + Mypy limpios |
| 6 | `make verify` | Validación completa (lint + test + architecture check) |

---

### Orden de Ejecución

```
1. Crear src/personality/prompt_renders.py (Fase 1)
2. Verificar import directo funciona
3. Modificar src/agents/specialists/__init__.py (Fase 2.1)
4. Modificar src/agents/__init__.py (Fase 2.2)
5. Modificar src/main.py lifespan (Fase 2.3)
6. Verificar que la app arranca correctamente
7. Crear tests unitarios (Fase 3)
8. make verify (Fase 4)
```

### Archivos Modificados (Resumen)

| Archivo | Acción |
|---|---|
| `src/personality/prompt_renders.py` | **CREAR** — módulo con 2 funciones puras |
| `src/agents/__init__.py` | **MODIFICAR** — eliminar import eager |
| `src/agents/specialists/__init__.py` | **MODIFICAR** — reemplazar imports eager por `register_all_specialists()` |
| `src/main.py` | **MODIFICAR** — añadir llamada a registro en `lifespan()` |
| `tests/unit/personality/test_prompt_renders.py` | **CREAR** — 8 tests unitarios |

### Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Algún otro módulo importa `src.agents.specialists.X` directamente (sin pasar por `__init__`) | El grep confirma que solo `__init__.py` los importa. Los imports directos como `from src.agents.specialists.cbt.cbt_tool import ...` siguen funcionando porque no dependen del `__init__.py` |
| El registro de especialistas debe ocurrir ANTES de la primera request | El `lifespan()` de FastAPI se ejecuta completamente antes de aceptar requests. Esto es garantizado por ASGI |
| El `orchestrator/__init__.py` también hace imports eager de `MasterOrchestrator` | No afecta porque `MasterOrchestrator` no depende transitivamente de `prompt_renders.py`. El `LazyMasterOrchestrator` solo usa el registry |
