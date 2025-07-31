# AEGEN: El Playbook Constitucional

> **Versión:** 5.0 (Edición Unificada y Definitiva)
> **Estado:** Prescriptivo y Vinculante

**Preámbulo:** Este documento es la única fuente de verdad y la constitución del proyecto AEGEN. Sintetiza la visión arquitectónica, la honestidad diagnóstica y la granularidad ejecutable de todas las propuestas anteriores (O, C, G). Su lectura y adhesión no son opcionales; son un prerrequisito para escribir una sola línea de código. La ignorancia de estas directrices resultará en el rechazo del trabajo.

## 📖 1. La Doctrina: Filosofía y Principios de Diseño

La doctrina de AEGEN se basa en la **Arquitectura Evolutiva y Pragmática**. No diseñamos para un futuro hipotético; construimos para la realidad presente con la capacidad innata de evolucionar.

1.  **Simplicidad Pragmática:** La complejidad solo se introduce si su Retorno de Inversión (ROI) es medible (ej. reducción de latencia, manejo de carga). Siempre se parte de la solución más simple.
2.  **Evolución Guiada por Evidencia:** La transición entre fases arquitectónicas (ej. Monolito → Distribuido) no es una decisión intuitiva. Es una acción detonada por el incumplimiento de umbrales cuantitativos específicos.
3.  **Declaratividad > Imperatividad:** Las APIs deben ser configurables, no scripts lineales. Esto es clave para la predictibilidad, el testing y la facilidad de uso por parte de agentes LLM.

    ```python
    # ❌ Imperativo: Difícil de entender y modificar por un LLM
    def process_data(user_id):
        user = db.get_user(user_id)
        if user.status == "active":
            # ...lógica compleja...

    # ✅ Declarativo: El "qué" está separado del "cómo"
    @workflow_registry.register("process_user")
    async def process_user_workflow(event: dict) -> ProcessResult:
        return await ProcessUserPipeline(
            user_id=event["user_id"],
            steps=[ValidateUser(), EnrichProfile()],
            output_format="json"
        ).execute()
    ```

4.  **LLM-First:** Cada fragmento de código, documentación y comentario debe ser fácil de parsear, entender y extender por un modelo de lenguaje. La claridad y la estructura explícita son obligatorias.

## 📜 2. La Ley: Estándares y Convenciones Ejecutables

Estas reglas son mandatorias y forzadas por herramientas automatizadas.

- **Tipado Estricto:** Obligatorio en toda interfaz pública. `Any` solo se permite con un comentario `TODO: [TICKET-ID] Justificar y reemplazar Any`. Forzado por `mypy --strict`.
- **Formato de Código:** No negociable. Forzado por `black` y `ruff`.
- **Organización de Imports:** Forzado por `ruff --select I`. Orden: `stdlib → third-party → internal`.

  ```python
  # ✅ Obligatorio
  # Standard library
  import asyncio
  from pathlib import Path

  # Third-party
  import httpx
  from pydantic import BaseModel

  # Internal
  from src.core.interfaces import IWorkflow
  from src.tools import WebSearchTool
  ```

- **Async I/O Obligatorio:** Toda operación de I/O (HTTP, DB, archivos) DEBE ser `async`. Prohibido el uso de librerías síncronas como `requests`.
- **Plantilla de Commit (Forzada por Git Hook):**

  ```
  feat(scope): resumen imperativo y conciso

  • WHY: El user-story o bug que resuelve.
  • WHAT: La solución técnica a alto nivel.
  • HOW: Archivos clave modificados, si es relevante.
  ```

- **Principio del Código de Referencia (La Regla del "Mejor que Esto"):**
  - **Directriz:** Antes de escribir una nueva clase o función, DEBES buscar un ejemplo existente de alta calidad en el codebase para usarlo como estándar mínimo.
  - **Arquetipo para `Tools`:** El archivo `src/tools/speech_processing.py` es el estándar de oro actual. Cualquier nueva `Tool` debe, como mínimo:
    1.  Estar encapsulada en una **Clase** para gestionar estado y dependencias.
    2.  Utilizar **Carga Diferida (Lazy Loading)** para recursos pesados (como modelos de ML).
    3.  Ejecutar operaciones bloqueantes (CPU o I/O síncrono) en un hilo separado usando `asyncio.to_thread` para no bloquear el event loop.
    4.  Integrarse con el ecosistema del proyecto (usar `settings` para configuración, decoradores como `@tool` si aplica).
    5.  Tener un manejo de errores robusto y logging contextualizado.

## 🏗️ 3. El Blueprint: Arquitectura y Diagnóstico de Estado

Este es el mapa completo del proyecto, incluyendo un **diagnóstico honesto y accionable** de su estado actual.

**Leyenda de Estado:**

- ✅: Implementado, probado y funcional.
- 🚧: Implementación parcial, requiere trabajo.
- ❌: No implementado o esqueleto. **BLOQUEANTE.**
- 🗑️: Obsoleto, candidato a eliminación.

```text
AEGEN/
├── Dockerfile                  # 🚧 Funcional, necesita target 'worker' para Fase 2.
├── compose.yml                 # 🚧 Funcional, necesita servicio 'worker' para Fase 2.
├── makefile                    # ✅ Comandos de conveniencia (dev, test, lint).
├── pyproject.toml              # ✅ Dependencias y configuración de tools.
├── .pre-commit-config.yaml     # ✅ Hooks de calidad (ruff, black, mypy).
├── PROJECT_OVERVIEW.md         # 📍 ESTE DOCUMENTO.
└── src/
    ├── main.py                 # ✅ Arranque FastAPI + middlewares + métricas.
    ├── api/                    # 🌐 Capa HTTP (routers + schemas).
    │   └── routers/
    │       ├── analysis.py     # ✅ POST /analysis/ingest.
    │       └── status.py       # ✅ GET /system/status, /metrics.
    ├── core/                   # 🏗️ Infraestructura y abstracciones.
    │   ├── interfaces/         # ✅ Contratos ABCs (IEventBus, IWorkflow, ITool).
    │   ├── bus/
    │   │   ├── in_memory.py    # ✅ Implementado y probado.
    │   │   └── redis.py        # ❌ Esqueleto para Fase 2.
    │   ├── engine.py           # ❌ MigrationDecisionEngine. CRÍTICO para evolución.
    │   ├── middleware.py       # ✅ Implementado y probado.
    │   ├── resilience.py       # ✅ Implementado y probado.
    │   ├── logging_config.py   # ✅ Logging JSON con trace_id.
    │   └── schemas.py          # ✅ Contratos Pydantic.
    ├── agents/                 # 🧠 Lógica de orquestación.
    │   ├── orchestrator.py     # 🚧 Coordinador con resiliencia básica.
    │   └── workflows/          # ❌ Esqueletos. Ningún workflow funcional.
    │       ├── base_workflow.py  # ❌ Falta la clase base abstracta.
    │       └── transcription/
    │           └── audio_transcriber.py # ❌ Placeholder.
    └── tools/                  # 🛠️ Funciones atómicas.
        ├── speech_processing.py  # ✅ Implementado y probado.
        └── telegram_interface.py # ❌ Placeholder.
└── tests/                      # 🚧 EN PROGRESO. Deuda técnica crítica siendo saldada.
    ├── conftest.py             # ✅ Fixtures base implementadas.
    ├── unit/                   # 🚧 EN PROGRESO. Replicando src/.
    │   └── core/               # ✅ Módulos base cubiertos.
    └── integration/            # ❌ Vacío.
```

## 🧪 4. La Garantía: Estrategia de Testing No Negociable

**Diagnóstico:** La falta de pruebas es la mayor debilidad y el mayor riesgo del proyecto. Esto es una emergencia técnica.

**Tooling y Cobertura Mínima (forzada por CI):**

| Capa                   | Tooling Mínimo                        | Cobertura Mínima            |
| :--------------------- | :------------------------------------ | :-------------------------- |
| **Unit (puro)**        | `pytest`, `factory-boy`               | 90% (branches)              |
| **Integration**        | `httpx.AsyncClient`, `respx`          | 85% (branches)              |
| **Contract (OpenAPI)** | `prance`, `schemathesis` (smoke)      | 100% de validez             |
| **Mutation (gating)**  | `mutmut` (solo en archivos cambiados) | < 3% de mutantes sobreviven |

**Ejemplo de Arranque Rápido (`tests/conftest.py`):**

```python
# Este código se implementa para desbloquear el desarrollo de pruebas.
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from src.main import app
from src.core.interfaces.bus import IEventBus

@pytest.fixture
async def async_client() -> AsyncClient:
    """Async test client para la app FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_event_bus() -> AsyncMock:
    """Mock del IEventBus para tests de integración."""
    mock = AsyncMock(spec=IEventBus)
    app.dependency_overrides[IEventBus] = lambda: mock
    yield mock
    app.dependency_overrides = {} # Limpiar después del test
```

## 🗺️ 5. El Plan de Batalla: Roadmap Evolutivo con Triggers

El roadmap no es una lista de deseos, es un plan de fases con detonantes observables.

#### FASE 0: WORKFLOW FUNDACIONAL (Prioridad Crítica)

- **Meta:** Implementar el primer flujo de valor de extremo a extremo, validando la arquitectura y entregando una capacidad tangible.
- **Workflow a Construir:** **Transcripción de Audio desde Telegram.**
- **Acciones Inmediatas:**
  1.  Implementar una `TelegramTool` para descargar archivos y enviar mensajes.
  2.  Implementar una `SpeechToTextTool` que use un modelo como Whisper.
  3.  Implementar el `TranscriptionWorkflow` que orqueste las dos herramientas.
  4.  Escribir tests unitarios para las tools y un test de integración para el workflow completo.
- **Definition of Done:** Un usuario puede enviar un audio a un bot de Telegram y recibir la transcripción como respuesta.

#### FASE 1: MONOLITO OBSERVABLE (Estado Actual Post-Fundación)

- **Arquitectura:** API y Worker en el mismo proceso. `InMemoryEventBus`.
- **Capacidades:** Logging JSON, métricas Prometheus, retries, idempotencia.

#### FASE 2: DISTRIBUCIÓN CONTROLADA (Evolución Guiada por Datos)

- **TRIGGER CUANTITATIVO:** El `MigrationDecisionEngine` devuelve `MIGRATE` cuando se cumple una de estas condiciones de forma sostenida (e.g., >5 min):
  - `p95_request_latency_ms > 500`
  - `cpu_utilization_percent > 85`
  - `in_memory_queue_depth > 1000`
- **Acciones:**
  1.  Activar la implementación de `RedisEventBus` mediante variable de entorno (`EVENT_BUS_TYPE=redis`).
  2.  Construir y desplegar el target `worker` del `Dockerfile`.
  3.  Escalar el servicio `worker` a `replicas=2` en `compose.yml`.

#### FASE 3: RESILIENCIA AVANZADA Y AUTOSCALING (Futuro)

- **Trigger:** Lag en la cola de Redis > 2000 mensajes por 5 min.
- **Acción:** Implementar KEDA + HPA para escalar los `worker` pods en Kubernetes.
- **Trigger:** Tasa de error con sistemas externos > 1%.
- **Acción:** Implementar patrón Circuit Breaker (`pybreaker`) y una Dead-Letter Queue (DLQ) en Redis.

## 🚀 6. La Cabina: Guía de Operaciones y Desarrollo

Comandos únicos para una experiencia de desarrollo consistente.

```bash
# Iniciar entorno de desarrollo completo con hot-reload
make dev

# Ejecutar suite completa de tests, cobertura y mutation testing
make test

# Verificar calidad de código (linting y tipado)
make lint

# Generar y validar documentación de la API
make docs
```

**Endpoints Clave (local):**

- **Swagger UI:** `http://localhost:8000/docs`
- **Métricas:** `http://localhost:8000/metrics`
- **Estado del Sistema:** `http://localhost:8000/system/status` (incluirá la recomendación del `MigrationDecisionEngine`).

## 🔧 7. Guía de Contribución (Humano & LLM-First)

### **Ciclo de Vida de una Funcionalidad (Flujo de Git Mandatorio)**

**Instrucción para Agente IA:** Antes de iniciar cualquier nueva funcionalidad, corrección o refactorización, DEBES seguir este ciclo. No se permite el `push` directo a `develop`. Cada unidad de trabajo debe ser encapsulada en un Pull Request.

**Paso 0: Sincronización de Contexto (Mandatorio)**
Antes de escribir una sola línea de código, debes tener un contexto absoluto del estado del proyecto. Este paso no es opcional.

1.  **Contexto Histórico (`¿De dónde venimos?`):**
    *   **Acción:** Lee el archivo `@history_llm_chat.txt`.
    *   **Objetivo:** Entender las decisiones, errores y correcciones recientes. Presta especial atención a las últimas 500 líneas para comprender el contexto inmediato de la última sesión de trabajo.

2.  **Contexto Real (`¿Dónde estamos?`):**
    *   **Acción:** Usa `glob` o `list_directory` para inspeccionar la estructura de archivos actual en `src/`.
    *   **Objetivo:** Verificar la existencia y el estado real de los componentes. No confíes ciegamente en la documentación; contrástala siempre con el código fuente. Este paso previene la creación de duplicados y la desalineación con la realidad.

3.  **Contexto Estratégico (`¿Para dónde vamos?`):**
    *   **Acción:** Estudia en detalle este documento (`@PROJECT_OVERVIEW.md`), específicamente el "Blueprint" y el "Plan de Batalla".
    *   **Objetivo:** Asegurarte de que la siguiente acción está alineada con la FASE actual del roadmap. Si encuentras una discrepancia entre el código real y este documento, tu primera tarea es corregir el documento.

**Paso 1: Sincronizar y Crear Rama**
Asegúrate de que tu `develop` local está actualizado con el repositorio remoto y crea una nueva rama descriptiva para tu tarea.

```bash
# Vuelve a la rama principal y trae los últimos cambios
git checkout develop
git pull origin develop

# Crea y muévete a tu nueva rama de funcionalidad
git checkout -b feature/nombre-descriptivo-de-la-tarea
```

**Paso 2: Desarrollar y Verificar Localmente**
Realiza los cambios de código en tu rama. Antes de considerar el trabajo terminado, DEBES cumplir el **Checklist Pre-Commit** de forma local.

```bash
# Ejecuta los linters y formateadores
make lint

# Ejecuta la suite de pruebas completa
make test
```
Solo si ambos comandos pasan sin errores, puedes continuar.

**Paso 3: Publicar y Crear Pull Request (PR)**
Sube tu rama al repositorio remoto y crea un Pull Request (PR) hacia `develop`.

```bash
# Sube tu rama al repositorio remoto
git push origin feature/nombre-descriptivo-de-la-tarea
```
- **Acción Manual/UI:** Ve a la interfaz de GitHub.
- **Crea el PR:** Configura el PR para fusionar tu rama (`feature/...`) en la rama `base: develop`.
- **Documenta el PR:** Usa la plantilla de commit para el título y la descripción, explicando el QUÉ y el PORQUÉ de tus cambios.

**Paso 4: Fusión y Limpieza**
- **Verificación de CI:** Espera a que todos los chequeos automáticos en el PR (GitHub Actions) se muestren en verde (✅). Si algo falla, vuelve al paso 2.
- **Fusionar:** Una vez aprobado y verificado, fusiona el PR usando el botón en la interfaz de GitHub.
- **Limpiar:** Elimina la rama de funcionalidad (`Delete branch`) después de la fusión para mantener el repositorio limpio.
- **Finalizar:** Vuelve al Paso 1 para la siguiente tarea.

---

- **Prompt de Sistema Interno:** Antes de generar código, lee `PROJECT_OVERVIEW.md`. Prioriza la claridad, sigue los estándares y escribe tests para toda nueva funcionalidad.
- **Checklist Pre-Commit (forzada por `pre-commit` hook):**
  1.  `make lint` pasa.
  2.  `make test` pasa y la cobertura se mantiene o aumenta.
  3.  `PROJECT_OVERVIEW.md` actualizado si hay cambios de arquitectura.
- **Ejemplo de "LLM-Hint" en Código:**

  ```python
  async def web_search(query: str) -> list[str]:
      """
      Realiza una búsqueda web usando un proveedor externo.

      LLM-hint: Esta es una función pura que encapsula I/O. No debe
      tener efectos secundarios en el estado del sistema. Su test debe
      usar 'respx' para mockear la llamada HTTP a la API de búsqueda.

      Args:
          query: La consulta de búsqueda.
      Returns:
          Una lista de resultados.
      """
      # ...código...
  ```

### VEREDICTO FINAL

Este playbook es la síntesis definitiva. Es **ejecutable**, porque proporciona el código y los comandos para salir de la deuda técnica actual. Es **estratégico**, porque define un roadmap de evolución basado en métricas observables y no en intuición. Y es **LLM-First**, porque cada sección está diseñada para ser un contexto claro y accionable para la generación de código asistida. **Se adopta este documento como la constitución final del proyecto.**
