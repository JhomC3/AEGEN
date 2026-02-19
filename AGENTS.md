# Directrices del Repositorio AEGEN

- Repositorio: https://github.com/JhomC3/aegen
- Stack: Python 3.13 · FastAPI · LangGraph · SQLite/sqlite-vec · Redis · Telegram
- Issues/PRs en GitHub: usar heredoc `<<'EOF'` para newlines reales; nunca `"\\n"` inline.

## Principios Core (Inmutables)

1. **Arquitectura Evolutiva:** De monolito funcional a sistema distribuido cuando las métricas lo justifiquen.
2. **Pragmatismo Medible:** Complejidad solo si ROI (Retorno de Inversión) > umbral definido.
3. **Gobernanza Automática:** Las reglas se ejecutan mediante scripts, no solo se recuerdan.
4. **LLM-First (IA Primero):** Diseñado para ser usado y entendido por Inteligencias Artificiales.
5. **Observabilidad Nativa:** Métricas y trazas implementadas desde el inicio.

## Estructura del Proyecto y Organización de Módulos

- Código fuente: `src/` (entrada principal en `src/main.py`).
- Tests: `tests/` con subdirectorios `unit/`, `integration/`, `performance/`, `prompts/`.
- Docs: `docs/` (arquitectura, guías, planes, reportes, investigación).
- ADRs: `adr/` (Architecture Decision Records; plantilla en `adr/plantilla-adr.md`).
- Scripts: `scripts/` (mantenimiento, quality gates, migraciones, webhooks).
- Storage: `storage/` (SQLite DB, backups, knowledge PDFs). No commitear datos reales.
- Prompts: `src/prompts/` (templates de prompts para agentes).
- Personalidad: `src/personality/` (Soul Stack de 5 capas, overlays de skills).
- Lockfiles: `requirements.lock` (prod), `requirements-dev.lock` (dev), `uv.lock`.
- Build output: `build/`, `dist/`, `*.egg-info` — todos en `.gitignore`.

```
src/
├── main.py                    # FastAPI entry point (lifespan, middleware, routers)
├── agents/
│   ├── orchestrator/          # MasterOrchestrator, factory, graph builder
│   │   └── routing/           # EnhancedRouter, intent patterns, routing analysis
│   ├── specialists/           # CBT specialist, Chat agent, Transcription agent
│   │   ├── cbt/               # CBT tools y prompt builder
│   │   └── chat/              # Chat tools y multimodal
│   └── utils/                 # Knowledge formatter, state utils
├── api/
│   ├── adapters/              # Telegram adapter
│   ├── middleware/             # API middleware
│   ├── routers/               # webhooks, status, llm_metrics, privacy
│   └── services/              # debounce, event processor, fragment consolidator
├── core/
│   ├── config/                # Settings por entorno (base, dev, prod)
│   ├── schemas/               # Modelos Pydantic (agents, api, graph, profile, etc.)
│   ├── interfaces/            # Interfaces abstractas (bus, specialist)
│   ├── bus/                   # Event bus (in-memory, redis)
│   ├── observability/         # Prometheus metrics, correlation, LLM wrapper
│   ├── logging/               # Formatters, types
│   ├── security/              # Access controller
│   ├── messaging/             # Message queue, user queue
│   ├── entitlements/          # Feature gating cache
│   └── prompts/               # Prompt loader
├── memory/
│   ├── sqlite_store.py        # SQLite persistence backend
│   ├── schema.sql             # DB schema definition
│   ├── migration.py           # Async idempotent migrations
│   ├── embeddings.py          # Embedding generation
│   ├── vector_search.py       # sqlite-vec vector similarity
│   ├── keyword_search.py      # FTS5 keyword search
│   ├── hybrid_search.py       # RRF hybrid ranking
│   ├── ingestion_pipeline.py  # Document ingestion
│   ├── knowledge_watcher.py   # Async file watcher (PDF auto-indexing)
│   ├── consolidation_worker.py # Background consolidation
│   ├── redis_buffer.py        # Redis message buffer
│   ├── repositories/          # Data access (memory_repo, profile_repo)
│   └── services/              # Memory summarizer, incremental extractor
├── personality/
│   ├── base/                  # IDENTITY.md + SOUL.md (capas 1-2)
│   ├── skills/                # Overlays: chat_overlay.md, tcc_overlay.md (capa 4)
│   ├── loader.py              # Carga de archivos de personalidad
│   ├── manager.py             # Lifecycle de personalidad
│   ├── prompt_builder.py      # Composición multi-capa del system prompt
│   └── style_analyzer.py      # "The Mirror" — detección de estilo lingüístico
├── tools/
│   ├── telegram/              # Cliente Telegram (client, download, forwarder)
│   ├── document_processing.py # PDF/DOCX/PPTX/XLSX
│   ├── image_processing.py    # Pillow + Tesseract
│   ├── multimodal_processor.py # Multimodal input
│   └── speech_processing.py   # Audio (yt-dlp)
└── prompts/                   # Templates (cbt_analysis.txt, transcription v1.yaml)
```

## Comandos de Desarrollo, Build y Testing

- Runtime: **Python >= 3.13**. Package manager: **uv**.
- Entorno virtual: `.venv/` (creado automáticamente por `make venv`).
- Si faltan dependencias o `command not found`, ejecutar `make install` y reintentar.
- Pre-commit hooks: `pre-commit install` (ruff check + ruff format + mypy + trailing whitespace + check-json + check-merge-conflict).

| Comando | Propósito |
|---|---|
| `make help` | Muestra todos los targets disponibles |
| `make venv` | Crea el entorno virtual con uv |
| `make install` | Sincroniza deps del lockfile + instala editable |
| `make lint` | Ejecuta linter (ruff) y type checker (mypy) |
| `make format` | Auto-format con ruff (format + check --fix) |
| `make test` | Ejecuta pytest (unit + integration) |
| `make verify` | **Validación completa:** lint + test + architecture check |
| `make coverage` | Tests con reporte de cobertura |
| `make dev-check` | Quick check de arquitectura solamente |
| `make run-dev` | Docker Compose up (app + polling + redis) |
| `make stop-dev` | Docker Compose down |
| `make logs-dev` | Tail logs de contenedores |
| `make build` | Build de imágenes Docker de producción |
| `make sync-docs` | Sincroniza docs con estado del proyecto |
| `make doctor` | Diagnóstico completo (git + docs sync + verify) |
| `make status` | Reporte de estado del proyecto |
| `make clean` | Elimina caches, venv, build artifacts |

- Docker Compose: 3 servicios — `app` (FastAPI, puerto 8000), `polling` (Telegram long-poll), `redis` (Alpine, 256MB, LRU eviction).
- CI (GitHub Actions): Ubuntu + uv + Python 3.13 → `make verify`. Triggers: push/PR a `main` y `develop`.

## Estándares de Código

- **Async First:** Todo I/O (red, base de datos, archivos) DEBE ser `async`. Sin excepciones (ruff rule `ASYNC`).
- **Tipado Estricto:** Uso obligatorio de `typing` y Pydantic. Mypy configurado en modo estricto (`disallow_untyped_defs`).
- **Formateador/Linter:** Ruff es el estándar único. Configuración estricta:
  - `T20`: Prohíbe `print()` (usar logging).
  - `C90`: Complejidad ciclomática max 10.
  - `S`: Reglas de seguridad (reemplaza bandit).
  - `PTH`: Usar `pathlib` en lugar de `os.path`.
- **Logging:** Usar `structlog` (preferido) o `logging` con `JsonFormatter`. Nunca usar `print()`.
- **Inmutabilidad:** Preferir paso de datos inmutables entre agentes. Usar Pydantic models como contratos.
- **Imports:** Agrupar: stdlib → third-party → local (ruff rule `I` lo enforce automáticamente).
- **Naming:** snake_case para funciones/variables, PascalCase para clases, UPPER_CASE para constantes. Archivos siempre en snake_case.
- **Límites de Tamaño:**
  - Funciones/Métodos: máximo **30 líneas** (recomendado) y complejidad ciclomática baja.
  - Archivos de Lógica (servicios, routers, agentes): objetivo **150 líneas**, máximo **200 líneas**.
  - Archivos de Definición (schemas Pydantic, configuraciones, modelos): máximo **300 líneas**.
  - Si se excede el máximo: evaluar división lógica en el siguiente ciclo. `scripts/simple_check.py` valida esto.
- **Seguridad Estática:** Ruff `S` (flake8-bandit) analiza vulnerabilidades en cada `make lint`.
- Nunca deshabilitar reglas de mypy/ruff a nivel de archivo completo. Corregir la causa raíz.

## Patrones de Arquitectura

- **Event-Driven:** `CanonicalEventV1` como lenguaje común. Todo pasa por el bus de eventos (`src/core/bus/`).
- **Registry Pattern:** Autodescubrimiento de especialistas y herramientas (`src/core/registry.py`).
- **State Graphs:** LangGraph para orquestación declarativa (`src/agents/orchestrator/graph_builder.py`).
- **Provenanced Memory:** Cada dato tiene origen, confianza y evidencia. Búsqueda híbrida: vector (sqlite-vec) + keyword (FTS5) + RRF ranking.
- **Soul Stack (5 capas):** Identidad → Alma → Espejo → Skill Overlay → Runtime context (`src/personality/`).
- **Inyección de Dependencias:** No instanciar clientes (Redis, SQLite, HTTP) dentro de funciones; recibirlos como argumentos. Ver `src/core/dependencies.py`.
- **Gestión de Errores:** Excepciones granulares en `src/core/exceptions.py`. Degradación suave (Graceful Degradation). Resiliencia con retry/backoff en `src/core/resilience.py`.

### Flujo de Datos

```
Telegram → Webhook (src/api/routers/webhooks.py)
  → TelegramAdapter (src/api/adapters/telegram_adapter.py)
  → CanonicalEventV1 (src/api/services/event_processor.py)
  → MasterOrchestrator (src/agents/orchestrator/master_orchestrator.py)
  → EnhancedRouter (src/agents/orchestrator/routing/enhanced_router.py)
  → Specialist Agent [CBT | Chat | Transcription]
  → Graph Execution (LangGraph)
  → Redis Buffer → Consolidation Worker → SQLite/sqlite-vec
  → Respuesta → Telegram
```

### Para Añadir un Nuevo Especialista

1. Definir la interfaz en `src/core/interfaces/specialist.py`.
2. Implementar en `src/agents/specialists/<nombre>_agent.py`.
3. Registrar en `src/core/registry.py` para autodescubrimiento.
4. Añadir prompt overlay en `src/personality/skills/<nombre>_overlay.md`.
5. Documentar en `docs/arquitectura/agentes/`.
6. Escribir tests en `tests/unit/` antes de la implementación.

## Guías de Testing

- Framework: **pytest** con `pytest-asyncio` (mode=auto), `pytest-cov`, `pytest-mock`, `pytest-snapshot`.
- Coverage: `--cov-fail-under=50` actual en pyproject.toml. Objetivo progresivo: 85%.
- Naming: `test_<funcionalidad>.py` colocados en el subdirectorio correspondiente:
  - `tests/unit/api/` — tests de routers y adapters
  - `tests/unit/core/` — tests de schemas, config, logging
  - `tests/unit/memory/` — tests de persistence, search, ingestion
  - `tests/unit/personality/` — tests del soul stack
  - `tests/unit/tools/` — tests de procesamiento
  - `tests/integration/` — tests end-to-end (API, conversación, memoria)
  - `tests/performance/` — benchmarks
- Fixtures compartidas: `tests/conftest.py`. Datos de fixture: `tests/fixture/`.
- Ejecutar SIEMPRE antes de push: `make verify` (lint + test + architecture check).
- Tests async: no necesitan decorador `@pytest.mark.asyncio` (mode=auto en pyproject.toml).
- Mocking: usar `pytest-mock` (fixture `mocker`). Para HTTP: usar `respx`.
- Snapshots: `pytest-snapshot` con `--snapshot-update` para regenerar.
- Pure test additions generalmente NO necesitan entrada en CHANGELOG.

## Flujo de Git y Pull Requests

- Branch principal de trabajo: `develop`. Branch de producción: `main`.
- **Commits atómicos:** Un commit por cambio lógico.
- **Formato de commit (Conventional Commits):**
  - `feat(scope): mensaje` — nueva funcionalidad
  - `fix(scope): mensaje` — corrección de bug
  - `refactor(scope): mensaje` — refactorización sin cambio de comportamiento
  - `style: mensaje` — cambios de formato/estilo
  - `docs(scope): mensaje` — cambios de documentación
  - `test(scope): mensaje` — adición o corrección de tests
  - `chore(scope): mensaje` — mantenimiento, dependencias, CI
- **Validación pre-commit:** `make verify` DEBE pasar al 100% (cero errores de Ruff, Mypy y arquitectura) antes de declarar una tarea como finalizada o realizar un commit. No se permiten excepciones "parciales".
- **PR Template:** `.github/PULL_REQUEST_TEMPLATE.md` — seguir el checklist de verificación.
- **CI Pipeline:** Push/PR a `main` o `develop` dispara `make verify` en Ubuntu.
- Agrupar cambios relacionados; no mezclar refactors no relacionados en el mismo PR.
- CHANGELOG.md: solo cambios visibles al usuario. Seguir formato Keep a Changelog + SemVer.

## Seguridad

- **Secretos:** NUNCA commitear `.env`, llaves API, tokens, o credenciales. Usar `.env.example` como plantilla.
- **Validación de Input:** Todo input de usuario DEBE ser validado mediante Schemas de Pydantic (`src/core/schemas/`).
- **Análisis Estático:** Ruff `S` (seguridad) en cada `make lint`. Pre-commit detecta llaves privadas.
- **No modificar** archivos de configuración de git o del sistema del usuario.
- **Redis:** Configurado con `maxmemory 256mb` y política `allkeys-lru`. No almacenar datos sensibles sin TTL.
- Nunca commitear o publicar números de teléfono reales, tokens reales, o valores de configuración vivos. Usar placeholders obviamente falsos en docs, tests, y ejemplos.

## Documentación

- **Idioma:** Toda la documentación en **Español**. Términos técnicos en inglés se permiten entre paréntesis ().
- **Fuente de Verdad:** `AGENTS.md` es el documento rector para agentes. La documentación detallada vive en `docs/`.
- **Estructura:**
  - Arquitectura detallada: `docs/arquitectura/` (subsistemas: agentes, core, memoria, personalidad, interfaces)
  - Guías operativas: `docs/guias/` (manual-desarrollo, manual-despliegue, manual-gestion-conocimiento)
  - Planes de desarrollo: `docs/planes/` (planes activos) y `docs/planes/archivo/` (completados)
  - Reportes: `docs/reportes/` (post-mortems, análisis forenses)
  - Investigación: `docs/investigacion/`
  - Ideas: `docs/IDEAS_Y_MEJORAS.md`
- **ADRs:** Architecture Decision Records en `adr/`. Usar `adr/plantilla-adr.md` como template. Hay 25 ADRs (13 archivados, 12 activos).
- **Changelog:** `CHANGELOG.md` sigue Keep a Changelog + Semantic Versioning. Solo cambios visibles al usuario.
- Cuando modifiques código, verificar si la documentación correspondiente necesita actualización.

## Planificación y Niveles de Cambio

### Niveles de cambio

No todo cambio merece el mismo proceso. La burocracia excesiva degrada la calidad tanto como la falta de proceso.

| Nivel | Ejemplos | Proceso requerido |
|---|---|---|
| **Trivial** | Fix de typo, ajuste de config, corrección de docs | Sin plan formal. Describir el cambio en el commit message. `make verify` si toca `.py`. |
| **Localizado** | Bug fix en un archivo, ajuste de lógica sin cambiar interfaces | Plan ligero: describir qué, por qué, y archivos afectados directamente en la conversación. `make verify` obligatorio. |
| **Estructural** | Cruza múltiples módulos, modifica interfaces/schemas, añade especialista, altera el pipeline | Plan formal con plantilla completa (`docs/planes/plantilla-plan.md`). Análisis de impacto, ADR si aplica. Aprobación del usuario antes de implementar. |

Los planes activos se almacenan en `docs/planes/`. Al completar un plan: cambiar su estado a "Completado" y moverlo a `docs/planes/archivo/`.

### Juicio técnico del agente

Las directrices de este documento constringen el **proceso de verificación**, no el **juicio técnico**. El agente debe:

- Proponer soluciones arquitectónicamente superiores cuando las identifique, incluso si difieren del plan aprobado o de la idea original del usuario. Esto incluye reorientar funcionalidades cuando una alternativa produce mejor resultado. Documentar la desviación.
- Elegir la solución más simple que resuelva el problema sin sobre-ingeniería.
- Evaluar si un cambio necesita plan formal o si la burocracia excede el valor del cambio.

### Antes de crear código nuevo (cambios localizados y estructurales)

1. Verificar si la funcionalidad ya existe (`grep` en `src/` por nombre, clase, o función similar).
2. **Solo para cambios estructurales:** Leer los ADRs relevantes en `adr/`, completar el Análisis de Impacto de la plantilla, verificar alineación con `PLAN-MAESTRO-ESTRATEGICO.md` en `docs/planes/`, y crear el plan en `docs/planes/` con formato `YYYY-MM-DD-nombre-descriptivo.md`.
3. Obtener aprobación explícita del usuario antes de implementar.
- Si una instrucción del usuario contradice los Principios Core de `AGENTS.md`, pedir aclaración antes de proceder.

### Cuándo es obligatorio un ADR

Un ADR es obligatorio si el cambio:
- Modifica interfaces en `src/core/interfaces/` o schemas en `src/core/schemas/`.
- Cambia contratos del bus de eventos (`CanonicalEventV1`).
- Añade o elimina un especialista en `src/agents/specialists/`.
- Altera el flujo de datos del pipeline (Telegram → Webhook → Evento → Router → Especialista → Respuesta).

Para cualquier otro cambio, un ADR no es necesario.

### Verificación durante la ejecución (Micro-Gates)

- **Archivos `.py` modificados:** Ejecutar `make verify` inmediatamente después de cada tarea. Si falla, la tarea está **bloqueada** -- no se puede avanzar a la siguiente. Corregir o revertir.
- **Schemas o interfaces modificados:** `make verify` + ejecutar el test de integración específico del subsistema afectado.
- **Solo documentación:** Verificación al final de todas las fases.
- **Regla absoluta:** No existe "deuda de verificación". Un fallo de verify no se pospone.

### Checklist pre-commit obligatorio

Antes de ejecutar `git add/commit`:
1. `git status` muestra SOLO archivos relacionados con el plan (sin archivos huérfanos ni olvidados).
2. Si se crearon archivos nuevos: confirmar que aparecen y agregarlos explícitamente.
3. Si se eliminaron archivos: `grep -r 'from <modulo_eliminado>' src/` confirma que nadie los importa.
4. `make verify` pasa al 100%.
5. Si el cambio toca el pipeline de mensajería: ejecutar `pytest tests/integration/test_telegram_webhook.py` y verificar con `grep -r 'from <modulo_modificado>' src/api/ src/agents/` que las dependencias del pipeline siguen intactas.

## Gestión de Dependencias

- Package manager: **uv** (https://github.com/astral-sh/uv).
- Dependencias definidas en `pyproject.toml` bajo `[project.dependencies]` y `[project.optional-dependencies]`.
- Lockfiles: `requirements.lock` (producción), `requirements-dev.lock` (desarrollo), `uv.lock`.
- **Agregar dependencia:** `uv add <package>` (actualiza pyproject.toml + lockfiles).
- **NO agregar dependencias** sin antes verificar si ya existe una alternativa en el proyecto. AEGEN ya incluye: httpx (HTTP), structlog (logging), Pydantic (validación), numpy/pandas (datos), Pillow/pytesseract (imágenes), pypdf/pymupdf (PDFs), aiosqlite (SQLite async), redis (cache/buffer).
- Build system: setuptools >= 65.0 + wheel.
- Instalar todo: `make install` (uv pip sync + editable install).

## Seguridad Multi-Agente

- No crear, aplicar, o eliminar `git stash` entries sin solicitud explícita. Asumir que otros agentes pueden estar trabajando.
- No cambiar de branch (`git checkout`, `git switch`) sin solicitud explícita.
- Cuando el usuario dice "commit", scope solo a tus cambios. Cuando dice "commit all", commitear todo en chunks agrupados.
- No crear/eliminar/modificar `git worktree` checkouts sin solicitud explícita.
- Si ves archivos no reconocidos en el working tree, continúa con tu trabajo; no los modifiques.
- Si lint/format genera cambios que son solo formato (no semánticos), auto-resolver sin preguntar. Si los cambios son semánticos (lógica, datos, comportamiento), preguntar.
- Cuando hagas `git pull`, usar `--rebase` para integrar cambios sin descartar el trabajo de otros agentes.

## Notas Específicas para Agentes

- **AEGEN** = infraestructura técnica (este repositorio). **MAGI** = la interfaz conversacional que el usuario ve.
- `AGENTS.md` es la fuente de verdad para directrices de agentes. Leerlo al iniciar una sesión de trabajo.
- Verificar con `make verify` que todo pasa antes de declarar cualquier tarea como finalizada.
- Responder con respuestas de alta confianza: verificar en código; no adivinar.
- Cuando trabajes en un Issue o PR de GitHub, imprimir la URL completa al final de la tarea.
- **Versión actual:** v0.8.4 según CHANGELOG.md.
- **Canales de mensajería:** al refactorizar lógica compartida, considerar el pipeline completo: Telegram → Webhook → Evento Canónico → Router → Especialista → Respuesta.
- Al añadir un nuevo AGENTS.md en cualquier subdirectorio, crear también un symlink `CLAUDE.md` apuntando al mismo archivo.

---
*Este documento unifica las reglas de operación de agentes y los estándares técnicos del proyecto. Si encuentras una forma mejor de trabajar, propón un cambio a AGENTS.md.*
