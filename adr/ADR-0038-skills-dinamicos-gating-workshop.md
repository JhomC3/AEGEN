# ADR-0038 - Skills Dinámicos: Gating Condicional, Hot-Reload y Skill Workshop

- **Fecha:** 2026-05-29
- **Estado:** Aceptado
- **Autor:** MAGI AI
- **ADR Relacionado:** ADR-0026 (Agentic Skills Hub), ADR-0037 (Bucle de Aprendizaje)

## Contexto

ADR-0026 estableció la arquitectura base de Skills Modulares Basados en Directorios (`SKILL.md` con YAML frontmatter + Markdown). El sistema actual carga skills de `src/personality/skills/` al arrancar. Tres capacidades están pendientes:

**1. Gating condicional:** Los skills se cargan siempre, independientemente de si sus prerequisitos están disponibles. Un skill de análisis cuantitativo que requiere `numpy` o una variable de entorno específica debería no cargarse si esas condiciones no se cumplen, en lugar de fallar en runtime.

**2. Hot-reload:** Cambios en `SKILL.md` requieren reiniciar el servidor FastAPI. Esto frena el desarrollo y la experimentación con prompts. El `KnowledgeWatcher` ya observa `storage/knowledge/`; la misma infraestructura puede extenderse a `src/personality/skills/`.

**3. Skill Workshop (auto-creación):** El sistema puede detectar que el usuario usa ciertos patrones de forma sistemática (ej. logging de entrenamientos, revisión de trading), pero no existe un mecanismo para que MAGI proponga o genere automáticamente un skill especializado para ese patrón.

Existe también `src/personality/skill_generator.py` en el codebase que no está documentado en `AGENTS.md`. Este ADR lo formaliza como la base del Skill Workshop.

## Principio arquitectónico: Skills NO requieren intents nuevos

La arquitectura de ruteo de AEGEN separa dos conceptos:

- **Intents (verbos):** Acciones fundamentales del usuario — `CHAT`, `PLANNING`, `SEARCH`. Son estáticos (11 valores en `IntentType`). El router usa estos verbos para decidir qué especialista atiende el mensaje.
- **Skills (overlays):** Dominios de conocimiento y herramientas — `fitness_tracker`, `nutrition_log`. Son dinámicos (el Skill Workshop los crea automáticamente). Se cargan como tools/prompts adicionales en los especialistas existentes.

Cuando el Skill Workshop crea un skill nuevo (ej. `fitness_tracker`), **no crea un intent nuevo**. Simplemente añade herramientas y contexto al especialista que ya maneja ese tipo de conversación (generalmente `CHAT` o `TASK_EXECUTION`). El LLM del especialista decide cuándo usar las tools del skill basándose en el contenido del mensaje.

La única razón para añadir un valor nuevo a `IntentType` es que surja un **tipo de workflow fundamentalmente nuevo** que ningún intent existente pueda representar. En la práctica esto es excepcional.


## Decisión

### 1. Gating Condicional en SKILL.md

Ampliar el YAML frontmatter de `SKILL.md` para soportar `requires`:

```yaml
---
name: "Quant Trading Specialist"
id: "quant_trading"
version: "1.0.0"
capabilities: ["trading", "quantitativo", "backtesting"]
requires:
  env:
    - ALPHA_VANTAGE_API_KEY
    - POLYGON_IO_KEY
  python_packages:
    - pandas
    - numpy
  bins:
    - git
priority: 8
---
```

El `skill_loader.py` evalúa `requires` antes de registrar el skill:

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
    """
    for env_var in requires.get("env", []):
        if not os.environ.get(env_var):
            return False  # Requisito no satisfecho

    for package in requires.get("python_packages", []):
        if importlib.util.find_spec(package) is None:
            return False  # Paquete no instalado

    for binary in requires.get("bins", []):
        if not shutil.which(binary):
            return False  # Binario no encontrado en PATH

    return True
```

Si `_check_requirements` retorna `False`, el skill se carga como `status="disabled"` (visible en `/system/skills/status` pero no inyectado en prompts). Los logs de arranque indican qué requisito falló.

### 2. Precedencia de Carga Multi-nivel

Skills en rutas de mayor precedencia sobreescriben los bundled:

```
Precedencia (mayor a menor):
1. storage/skills/user/     ← Skills creados por el usuario/MAGI dinámicamente
2. storage/skills/          ← Skills instalados por el administrador
3. src/personality/skills/  ← Skills bundled del core
```

Si `storage/skills/chat/SKILL.md` existe, reemplaza a `src/personality/skills/chat/SKILL.md`. El `skill_loader.py` escanea las rutas en orden de precedencia y descarta duplicados (mismo `id`).

Esto permite:
- Personalizar un skill bundled sin modificar el código fuente.
- El Skill Workshop guarda en `storage/skills/user/` sin tocar `src/`.

### 3. Hot-Reload de Skills

Extender `KnowledgeWatcher` (`src/memory/knowledge_watcher.py`) para también observar cambios en los directorios de skills:

```python
_WATCH_DIRS = [
    Path(settings.STORAGE_DIR) / "knowledge",   # Ya existente
    Path(settings.STORAGE_DIR) / "skills",       # NUEVO
    Path("src/personality/skills"),              # NUEVO (solo en dev mode)
]
```

Al detectar un cambio en un `SKILL.md`:
1. Re-parsear el archivo con `skill_parser.py`.
2. Si el skill ya está cargado, actualizarlo en el `PersonalityManager` sin reiniciar.
3. Publicar evento `skill.reloaded` en el bus para que los workers lo registren.
4. Si el cambio rompe el YAML, loguear el error y mantener la versión anterior.

El hot-reload en producción solo se activa para `storage/skills/` (no para `src/personality/skills/`, que requiere un deploy controlado).

### 4. Skill Workshop (Auto-creación por MAGI)

Formalizar `skill_generator.py` como el motor del Skill Workshop. El workflow es:

**Trigger:** El `ConsolidationWorker` detecta que el usuario ha completado N (default: 5) sesiones con un patrón similar (ej. logging de entrenamiento, análisis de noticias). Publica evento `pattern.detected` con el patrón identificado.

**Generación del SKILL.md:**

```python
async def generate_skill_from_pattern(
    pattern_description: str,
    example_interactions: list[dict],
    skill_id: str,
) -> Path:
    """
    Usa el LLM analítico para generar un SKILL.md completo
    a partir de un patrón de interacción observado.
    """
    prompt = SKILL_WORKSHOP_PROMPT.format(
        pattern=pattern_description,
        examples=format_examples(example_interactions),
    )
    skill_content = await get_analytical_llm().ainvoke(prompt)

    # Validar YAML frontmatter antes de guardar
    parsed = skill_parser.parse(skill_content)
    parsed.id = skill_id

    output_path = Path(settings.STORAGE_DIR) / "skills" / "user" / skill_id / "SKILL.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(skill_content)

    return output_path
```

**Validación y aprobación:** El skill generado se guarda con `status: draft` en el frontmatter. El administrador recibe una notificación por Telegram con el contenido del skill y dos opciones: "Activar" o "Rechazar". Al activar, se cambia `status: active` y el hot-reload lo carga automáticamente.

**El SKILL.md generado tiene un formato estándar:**

```yaml
---
name: "Fitness Tracker"
id: "fitness_tracker"
version: "1.0.0"
status: "draft"           # Requiere aprobación
generated_by: "skill_workshop"
generated_at: "2026-05-29T10:00:00Z"
capabilities: ["fitness", "entrenamiento", "nutricion"]
priority: 6
---
## Propósito
[Descripción del patrón detectado]

## Instrucciones
[Protocolo específico generado por el LLM]

## Ejemplos de Activación
- "Entrené hoy 45 minutos de cardio"
- "¿Cómo va mi racha de entrenamientos?"
```

## Consecuencias

### Positivas
- **Extensibilidad sin código:** El administrador puede personalizar el comportamiento de MAGI editando archivos en `storage/skills/` sin tocar el código fuente.
- **Skills condicionadas a entorno:** Un skill de trading que requiere API keys específicas no falla en arranque — simplemente no se carga hasta que las keys estén configuradas.
- **Desarrollo ágil:** Hot-reload elimina el ciclo reinicio-prueba al iterar sobre prompts.
- **Evolución autónoma:** El Skill Workshop permite que MAGI proponga nuevas habilidades basadas en patrones de uso real, reduciendo la carga del desarrollador.

### Negativas / Riesgos
- **Seguridad de skills dinámicos:** Skills en `storage/skills/user/` pueden incluir `tools.py` con código arbitrario. La carga dinámica de Python sin sandboxing es un vector de ataque. **Decisión:** En v0.9.x, `tools.py` en skills dinámicos está **deshabilitado**. Solo se carga el `SKILL.md` (prompt). La carga de tools requiere review del desarrollador y moverlo a `src/personality/skills/`.
- **Calidad de skills auto-generados:** El LLM puede generar skills con instrucciones contradictorias o demasiado genéricas. La revisión humana (aprobación via Telegram) mitiga esto en la primera versión.
- **Proliferación de skills:** Sin el curador de ADR-0037, la carpeta `storage/skills/user/` puede crecer indefinidamente. El curador gestiona esto con los umbrales de `stale` y `archived`.
- **Hot-reload en producción:** Un archivo `SKILL.md` corrupto puede dejar el `PersonalityManager` en estado inconsistente. La validación YAML antes del swap y la retención de la versión anterior son obligatorias.
