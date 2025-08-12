# AEGEN: El Playbook Constitucional

> **Versión:** 7.0 (Edición Foco-Total)
> **Estado:** Prescriptivo y Vinculante

**Preámbulo:** Este documento es la única fuente de verdad y la constitución del proyecto AEGEN. Tras una re-evaluación estratégica, se adopta una arquitectura nativa de LangChain para construir una plataforma de agentes federados. Su lectura y adhesión son un prerrequisito para escribir una sola línea de código.

## 📖 1. La Doctrina: Filosofía y Principios de Diseño

La doctrina de AEGEN se basa en la **Arquitectura Evolutiva y Pragmática**.

1.  **Simplicidad Pragmática:** La complejidad solo se introduce si su Retorno de Inversión (ROI) es medible. Se empieza simple y se evoluciona hacia la complejidad solo cuando un requisito funcional lo exige explícitamente.
2.  **Evolución Guiada por Evidencia:** La transición entre fases arquitectónicas (ej. Monolito → Distribuido) es una acción detonada por el incumplimiento de umbrales cuantitativos específicos.
3.  **Orquestación Basada en LangGraph:** La lógica de los agentes se modela como grafos de estado (`StateGraph`). Esto proporciona una estructura declarativa, observable (vía LangSmith) y extensible para flujos complejos, reemplazando la orquestación personalizada.
4.  **LLM-First:** Cada componente debe ser fácil de entender y usar por un modelo de lenguaje. La claridad, la modularidad y las interfaces bien definidas son obligatorias.
5.  **Abstracción de Canales:** El núcleo de los agentes debe ser agnóstico a la fuente de datos (Telegram, Discord, etc.). Esto se logra mediante una capa de **Adaptadores de Entrada** que traducen los eventos específicos de cada canal a un **Evento Canónico Interno**.

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

- **Principio del Código de Referencia (La Regla del "Mejor que Esto")**:
  - **Directriz:** Antes de escribir una nueva clase o función, DEBES buscar un ejemplo existente de alta calidad en el codebase para usarlo como estándar mínimo.
  - **Arquetipo para `Tools`:** El archivo `src/tools/speech_processing.py` sigue siendo el estándar de oro para el diseño de herramientas (ahora decoradas con `@tool` de LangChain). Cualquier nueva `Tool` debe, como mínimo, seguir su patrón de diseño:
    1.  **Separación de Responsabilidades:** Implementar una clase **Manager** (ej. `WhisperModelManager`) para la gestión de recursos pesados (modelos, conexiones). Esta clase debe ser un Singleton para asegurar una única instancia.
    2.  **Carga Diferida (Lazy Loading):** El recurso pesado (ej. el modelo de ML) no se carga en el `__init__`, sino en una función `get_model()` asíncrona la primera vez que se necesita.
    3.  **Ejecución No Bloqueante:** Las operaciones bloqueantes (CPU o I/O síncrono) DEBEN ejecutarse en un hilo separado usando `asyncio.to_thread` para no detener el event loop principal.
    4.  **Interfaz de Herramienta Limpia:** La función expuesta como herramienta (decorada con `@tool`) debe ser simple, asíncrona y delegar la lógica compleja al Manager.
    5.  **Integración con el Ecosistema:** Usar `settings` para configuración y tener un manejo de errores robusto con logging contextualizado.

## 🏗️ 3. El Blueprint: Arquitectura y Diagnóstico de Estado

**Leyenda de Estado:**

- ✅: Implementado
- 🚧: En progreso
- ❌: No implementado

```text
AEGEN/
├── Dockerfile                  # 🚧 A actualizar con dependencias de LangChain.
├── compose.yml                 # ✅ Sin cambios para la Fase 1.
├── pyproject.toml              # 🚧 A actualizar con dependencias de LangChain.
├── .pre-commit-config.yaml     # ✅ Sin cambios.
├── PROJECT_OVERVIEW.md         # 📍 ESTE DOCUMENTO.
└── src/
    ├── main.py                 # 🚧 A refactorizar para invocar el grafo de transcripción.
    ├── api/
    │   └── routers/
    │       └── webhooks.py     # 🚧 A refactorizar como "Adaptador de Telegram".
    ├── core/
    │   ├── schemas.py          # 🚧 A actualizar con CanonicalEvent y TranscriptionState.
    │   └── ...
    ├── agents/                 # 🧠 Lógica de orquestación basada en LangGraph.
    │   ├── graph_state.py      # ❌ (Fase 1) A crear.
    │   └── specialists/        # ❌ (Fase 1) Directorio para los agentes especializados.
    │       └── transcription_agent.py # ❌ (Fase 1) A crear.
    └── tools/                  # 🛠️ Funciones atómicas, a envolver con @tool de LangChain.
        ├── speech_processing.py  # 🚧 A adaptar con @tool.
        ├── telegram_interface.py # 🚧 A adaptar con @tool.
└── tests/                      # 🚧 A reconstruir en paralelo con el desarrollo.
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

## 🗺️ 5. El Plan de Batalla: Roadmap de la Plataforma de Agentes

El roadmap se re-enfoca para priorizar la entrega de un resultado funcional tangible antes de abordar la complejidad futura, sin perder la visión estratégica.

#### FASE 1: AGENTE DE TRANSCRIPCIÓN END-TO-END (Foco Actual)

- **Meta:** Lograr una "victoria rápida" que valide la nueva arquitectura y restaure la confianza en el proceso. El único objetivo es que un usuario envíe un audio a Telegram y reciba una transcripción, procesada de principio a fin por un agente de LangGraph.
- **Acciones Clave (Lineales y Enfocadas):**
    1.  **Configurar Entorno:** Automatizar el webhook de Telegram usando `pyngrok` para eliminar el flujo manual de `curl`.
    2.  **Definir Contratos Mínimos:** Añadir a `schemas.py` únicamente los schemas `CanonicalEvent` y `TranscriptionState` necesarios para este flujo.
    3.  **Adaptar Herramientas Mínimas:** Envolver las funciones necesarias en `telegram_interface.py` y `speech_processing.py` con el decorador `@tool` de LangChain.
    4.  **Construir Grafo de Transcripción:** Crear un grafo simple y lineal en `transcription_agent.py` con tres nodos: `descargar_audio`, `transcribir_audio`, `responder_telegram`.
    5.  **Conectar Webhook al Grafo:** Refactorizar `webhooks.py` para que actúe como un adaptador que convierte el update de Telegram en un `CanonicalEvent` e invoca **directamente** al grafo de transcripción.
    6.  **Probar Flujo Completo:** Verificar que el sistema funciona de extremo a extremo.

#### FASE 2: MVP DEL AGENTE RAG Y EL ENRUTADOR MAESTRO (Visión a Futuro)

- **Meta:** Construir el primer flujo de valor complejo, validando la arquitectura de agentes federados.
- **Prerrequisito:** Éxito y validación de la Fase 1.
- **Acciones Clave:** Construir el `RAGAgent` y un `MasterRouter` que pueda despachar tareas al agente de RAG o al de transcripción.

#### FASE 3: EXPANSIÓN DE LA FEDERACIÓN Y LA PLATAFORMA (Visión a Futuro)

- **Meta:** Añadir más agentes (Análisis Financiero, Reportes) y enriquecer la plataforma con memoria a largo plazo y colas de tareas diferenciadas.

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

    - **Acción:** Lee el archivo `@history_llm_chat.txt`.
    - **Objetivo:** Entender las decisiones, errores y correcciones recientes. Presta especial atención a las últimas 500 líneas para comprender el contexto inmediato de la última sesión de trabajo.

2.  **Contexto Real (`¿Dónde estamos?`):**

    - **Acción:** Usa `glob` o `list_directory` para inspeccionar la estructura de archivos actual en `AEGEN/`.
    - **Objetivo:** Verificar la existencia y el estado real de los componentes. No confíes ciegamente en la documentación; contrástala siempre con el código fuente. Este paso previene la creación de duplicados y la desalineación con la realidad.

3.  **Contexto Estratégico (`¿Para dónde vamos?`):**
    - **Acción:** Estudia en detalle este documento (`@PROJECT_OVERVIEW.md`), específicamente el "Blueprint" y el "Plan de Batalla".
    - **Objetivo:** Asegurarte de que la siguiente acción está alineada con la FASE actual del roadmap. Si encuentras una discrepancia entre el código real y este documento, tu primera tarea es corregir el documento.

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
      Returns:          Una lista de resultados.
      """
      # ...código...
  ```

### VEREDICTO FINAL

Este documento, en su versión 7.0, establece un plan de acción inmediato y enfocado, sin perder de vista la arquitectura definitiva basada en una federación de agentes orquestada por LangGraph. **Se adopta este documento como la constitución para el trabajo a continuación.**
