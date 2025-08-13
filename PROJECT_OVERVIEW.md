# AEGEN: El Playbook Constitucional

> **Versión:** 8.0 (Edición Post-Fase 1)
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
  - **Arquetipo para `Tools`:** El archivo `src/tools/speech_processing.py` sigue siendo el estándar de oro para el diseño de herramientas (ahora decoradas con `@tool` de LangChain).
  - **NUEVO - Principio de Orquestación de Archivos:** Basado en la lección aprendida en la Fase 1:
    - **Regla:** Las `Tools` deben ser, en la medida de lo posible, sin estado y no deben gestionar la creación o eliminación de archivos en el sistema. La responsabilidad del ciclo de vida de los archivos (creación, lectura, eliminación) recae en el **orquestador** (ej. la tarea de fondo en `webhooks.py`).
    - **Implementación:** El orquestador debe usar directorios temporales (`tempfile.TemporaryDirectory`) para manejar los archivos necesarios para una tarea. La ruta a estos archivos se pasa explícitamente a las `Tools`. Esto asegura que los archivos no persistan innecesariamente y que las `Tools` sean más puras y reutilizables.

## 🏗️ 3. El Blueprint: Arquitectura y Diagnóstico de Estado

**Leyenda de Estado:**
- ✅: Implementado y Validado
- 🎯: Foco Actual
- 🚧: En Progreso
- ❌: No Implementado

```text
AEGEN/
├── Dockerfile                  # ✅ Configuración base robusta.
├── compose.yml                 # ✅ Sin cambios.
├── pyproject.toml              # 🚧 A actualizar con dependencias de LangChain.
├── PROJECT_OVERVIEW.md         # 📍 ESTE DOCUMENTO.
└── src/
    ├── main.py                 # ✅ Routers configurados.
    ├── api/
    │   └── routers/
    │       └── webhooks.py     # ✅ Refactorizado para robustez con temp files.
    ├── core/
    │   ├── schemas.py          # ✅ Schemas de Fase 1 implementados.
    │   └── ...
    ├── agents/                 # 🧠 Lógica de orquestación basada en LangGraph.
    │   └── specialists/
    │       └── transcription_agent.py # ✅ Agente agnóstico implementado.
    └── tools/                  # 🛠️ Funciones atómicas, envueltas con @tool.
        ├── speech_processing.py  # ✅ Adaptado con @tool.
        ├── telegram_interface.py # ✅ Refactorizado para aceptar path de destino.
└── tests/                      # 🚧 En progreso (Test de integración clave añadido).
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

#### ✅ FASE 1: AGENTE DE TRANSCRIPCIÓN END-TO-END (Completada)

- **Meta:** Lograr una "victoria rápida" que valide la nueva arquitectura. Un usuario envía un audio a Telegram y recibe una transcripción.
- **Resultado:** **Éxito.** El flujo funciona de manera robusta y limpia.
- **Acciones Clave Realizadas:**
    1.  **Configurar y Probar Entorno:** Se validó el entorno local con Docker.
    2.  **Depurar Test de Integración:** Se corrigió un test E2E (`test_telegram_webhook.py`) que fallaba por un payload incorrecto, desbloqueando la validación del flujo.
    3.  **Depurar Flujo Real:** Se diagnosticó un `AttributeError` en tiempo de ejecución debido a una configuración faltante (`TELEGRAM_DOWNLOAD_DIR`).
    4.  **Refactorizar para Robustez:** En lugar de simplemente añadir la configuración, se refactorizó el flujo para usar directorios temporales, eliminando la dependencia de una carpeta fija y asegurando la limpieza automática de archivos. Esto implicó:
        - Modificar `telegram_interface.py` para que la herramienta de descarga sea más flexible.
        - Modificar `webhooks.py` para orquestar la creación y eliminación de archivos temporales.
    5.  **Validación Final:** Se confirmó el éxito del flujo completo con una prueba manual.

#### 🎯 FASE 2: MVP DEL AGENTE RAG Y EL ENRUTADOR MAESTRO (Foco Actual)

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
    - **Objetivo:** Entender las decisiones, errores y correcciones recientes.

2.  **Contexto Real (`¿Dónde estamos?`):**
    - **Acción:** Usa `glob` o `list_directory` para inspeccionar la estructura de archivos actual.
    - **Objetivo:** Verificar la existencia y el estado real de los componentes.

3.  **Contexto Estratégico (`¿Para dónde vamos?`):**
    - **Acción:** Estudia en detalle este documento (`@PROJECT_OVERVIEW.md`).
    - **Objetivo:** Asegurarte de que la siguiente acción está alineada con la FASE actual del roadmap.

4.  **NUEVO - Contexto de Ejecución (`¿Cómo funciona?`):**
    - **Acción:** Revisa `Dockerfile`, `compose.yml` y `makefile` para entender cómo se construye y ejecuta la aplicación.
    - **Objetivo:** No asumir que las dependencias o herramientas de sistema (como `ffmpeg`) simplemente existen; verifícalo. Este paso es clave para el debugging.

**Paso 1: Sincronizar y Crear Rama**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/nombre-descriptivo-de-la-tarea
```

**Paso 2: Desarrollar y Verificar Localmente**
```bash
make lint
make test
```

**Paso 3: Publicar y Crear Pull Request (PR)**
```bash
git push origin feature/nombre-descriptivo-de-la-tarea
```

**Paso 4: Fusión y Limpieza**
- Espera a que los chequeos de CI pasen (✅).
- Fusiona el PR.
- Elimina la rama.

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

Este documento, en su versión 8.0, refleja la finalización exitosa de la Fase 1 y establece un plan de acción claro para la Fase 2. **Se adopta este documento como la constitución para el trabajo a continuación.**
