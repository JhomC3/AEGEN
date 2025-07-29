# 🤖 AEGEN: Sistema de Agentes bajo la Arquitectura de Evolución Pragmática Unificada (AEP-U)

## 📖 **Introducción y Filosofía**

**AEGEN** es un sistema de agentes inteligentes diseñado para ser robusto, escalable y mantenible. Su desarrollo se guía por la **Arquitectura de Evolución Pragmática Unificada (AEP-U)**, una estrategia operativa que prioriza la simplicidad, la observabilidad y la evolución basada en evidencia.

La AEP-U nos permite comenzar con un **monolito inteligente** que es rápido de desarrollar y, a medida que las métricas del sistema lo justifiquen, evolucionar de manera controlada y automatizada hacia una arquitectura distribuida, evitando la sobreingeniería y la complejidad prematura.

---

## 🏗️ **Arquitectura del Sistema**

La arquitectura de AEGEN está diseñada para evolucionar en tres fases claras.

### **Fase 1: El Monolito Inteligente y Resiliente (Estado Actual)**

Actualmente, AEGEN opera como un sistema monolítico contenido en un único servicio Docker. Aunque es un monolito, está internamente desacoplado gracias a un bus de eventos asíncrono en memoria.

- **API (FastAPI):** Recibe las peticiones y las publica como eventos en el bus.
- **IEventBus (InMemoryEventBus):** Un bus de eventos en memoria (`asyncio.Queue`) que desacopla la recepción de la tarea de su procesamiento.
- **Workers (Background Tasks):** Consumidores de eventos que se ejecutan como tareas de fondo dentro del mismo proceso de la API, gestionados por el `InMemoryEventBus`.
- **WorkflowRegistry:** Permite el descubrimiento y la ejecución de flujos de trabajo de manera dinámica.

```
┌───────────────────────────────────────────────────┐
│                   Servicio AEGEN (Contenedor Docker)                  │
│ ┌───────────────────────────────────────────────┐ │
│ │                    FastAPI App                  │ │
│ │ ┌───────────────┐   ┌───────────────────────┐ │ │
│ │ │ Endpoint /api │──▶│     IEventBus         │ │ │
│ │ └───────────────┘   │ (InMemoryEventBus)    │ │ │
│ │                     └───────────┬───────────┘ │ │
│ └─────────────────────────────│─────────────────┘ │
│                               │                   │
│ ┌─────────────────────────────▼─────────────────┐ │
│ │            Workers (asyncio.create_task)      │ │
│ │ ┌───────────────┐   ┌───────────────────────┐ │ │
│ │ │   Worker 1    │◀──│  WorkflowRegistry     │ │ │
│ │ │   Worker 2    │   │ (Descubre Workflows)  │ │ │
│ │ │     ...       │   └───────────────────────┘ │ │
│ │ └───────────────┘                             │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### **Fase 2: Transición Controlada a Distribuido (Roadmap Futuro)**

Cuando el `MigrationDecisionEngine` (un componente futuro) detecte que se han superado los umbrales de rendimiento (latencia, CPU), el sistema evolucionará:

1.  **Cambio de Implementación:** Se activará el `RedisEventBus` mediante una variable de entorno.
2.  **Despliegue Separado:** Los workers se ejecutarán en sus propios contenedores, permitiendo el escalado horizontal independiente de la API.

### **Fase 3: Madurez Operativa (Roadmap Futuro)**

En esta fase, se introducirán optimizaciones avanzadas solo donde sea necesario:

-   **Workers Especializados:** Colas y workers dedicados por tipo de tarea para un escalado granular.
-   **Patrones Avanzados:** Implementación condicional de Sagas o Circuit Breakers para flujos de trabajo complejos.
-   **Observabilidad Distribuida:** Tracing completo con OpenTelemetry.

---

## 🗺️ **Hoja de Ruta Evolutiva (Roadmap)**

El sistema está preparado para evolucionar a través de las siguientes fases, guiadas por métricas:

-   **Fase 2: Transición Controlada a Distribuido**
    -   **Disparador**: Superar umbrales de rendimiento (e.g., latencia P95 > 500ms, carga de CPU > 85%) monitoreados por un futuro `MigrationDecisionEngine`.
    -   **Acción**: Cambiar la implementación del `IEventBus` a `RedisEventBus` (usando Redis Streams) mediante una variable de entorno. Desplegar los workers en contenedores separados para escalar horizontalmente.

-   **Fase 3: Madurez Operativa y Especialización**
    -   **Disparador**: Necesidad de optimización de costos o gestión de carga granular en tareas específicas.
    -   **Acción**: Crear colas de eventos especializadas por tipo de tarea en Redis. Implementar patrones avanzados (Sagas, Circuit Breakers) solo donde sea estrictamente necesario y validado por reglas de CI. Integrar tracing distribuido completo con OpenTelemetry.

---

## 📁 **Estructura del Proyecto**

La estructura de directorios está organizada para reflejar la separación de conceptos y facilitar la evolución.

```
AEGEN/
├── 📄 .dockerignore
├── 📄 .env.example
├── 📄 .gitignore
├── 📄 .pre-commit-config.yaml
├── 📄 compose.yml
├── 📄 docker-compose.override.yml
├── 📄 docker-compose.yml
├── 📄 Dockerfile
├── 📄 makefile
├── 📄 pyproject.toml
├── 📄 README.md
├── 📄 PROJECT_OVERVIEW.md
├── 🗂️ data/
├── 🗂️ docs/
├── 🗂️ notebooks/
├── 🗂️ scripts/
├── 🗂️ src/
│   ├── 📄 main.py                     # Punto de entrada de FastAPI y configuración
│   ├── 🗂️ agents/                    # Lógica de agentes y workflows
│   │   └── 🗂️ workflows/
│   ├── 🗂️ api/                       # Endpoints de la API (Routers)
│   │   └── 🗂️ routers/
│   ├── 🗂️ core/                      # Núcleo de la aplicación
│   │   ├── 📄 dependencies.py
│   │   ├── 📄 error_handling.py
│   │   ├── 📄 exceptions.py
│   │   ├── 📄 logging_config.py
│   │   ├── 📄 registry.py             # WorkflowRegistry
│   │   ├── 📄 schemas.py
│   │   ├── 🗂️ bus/                   # Implementaciones de IEventBus
│   │   │   └── 📄 in_memory.py
│   │   ├── 🗂️ config/                # Gestión de configuración
│   │   └── 🗂️ interfaces/            # Contratos (ABCs)
│   │       ├── 📄 bus.py
│   │       ├── 📄 tool.py
│   │       └── 📄 workflow.py
│   ├── 🗂️ tools/                     # Herramientas reutilizables
│   └── 🗂️ vector_db/                 # Interacción con BD vectorial
└── 🗂️ tests/                         # Pruebas unitarias y de integración
```

---

## 🔧 **Tecnologías Principales**

-   **🐍 Python 3.13**
-   **⚡ FastAPI**: Framework web asíncrono.
-   **📦 Pydantic**: Validación de datos.
-   **📝 StructLog**: Logging estructurado para observabilidad.
-   **Prometheus & Grafana**: Para métricas y monitorización.
-   **🔴 Redis**: Preparado para actuar como message broker en Fase 2.
-   **🐳 Docker & Docker Compose**: Para containerización y orquestación.
-   **✅ Ruff, Black, MyPy**: Herramientas de calidad de código.

---

## 🚀 **Inicio Rápido**

### **Prerrequisitos**
-   Docker y Docker Compose

### **Instalación y Ejecución**

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/JhomC3/aegen.git
    cd aegen
    ```

2.  **Configurar variables de entorno:**
    ```bash
    cp .env.example .env
    # Edita .env si necesitas añadir claves de API para las herramientas
    ```

3.  **Levantar los servicios con Docker Compose:**
    Este comando construirá la imagen de la aplicación y levantará los servicios definidos en `compose.yml` (API, Redis, etc.).
    ```bash
    make up
    ```
  3.  **Ejecutar con Docker Compose:**
    ```bash
    docker compose up -d --build
    ```

4.  **(Alternativa) Ejecutar localmente para desarrollo:**
    ```bash
    # Asegúrate de tener las dependencias instaladas con `poetry install`
    poetry run uvicorn src.main:app --reload --port 8000
    ```

5.  **Acceder a la API:**
    La documentación de la API estará disponible en [http://localhost:8000/docs](http://localhost:8000/docs).

-   **Endpoint de Análisis:**
    Envía una petición POST al endpoint principal para iniciar un flujo de trabajo.
    ```http
    POST http://localhost:8000/api/v1/analysis/
    Content-Type: application/json

    {
      "query": "Analiza los riesgos del protocolo Uniswap V4"
    }
    ```
    La API devolverá un `HTTP 202 Accepted` inmediatamente, y el trabajo se procesará en segundo plano.

---
*Documentación actualizada según la Arquitectura de Evolución Pragmática Unificada (AEP-U). Versión 1.0.0*
