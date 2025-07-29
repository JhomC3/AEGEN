# 🤖 AEGEN: Sistema de Agentes con Arquitectura Evolutiva

## 📖 **Introducción y Filosofía**

**AEGEN** es un sistema de agentes inteligentes diseñado para ser robusto, escalable y mantenible. Su desarrollo se guía por una **arquitectura evolutiva y pragmática**, una estrategia que prioriza la simplicidad, la observabilidad y la evolución basada en evidencia.

Este enfoque nos permite comenzar con un **monolito inteligente** que es rápido de desarrollar y, a medida que las métricas del sistema lo justifiquen, evolucionar de manera controlada y automatizada hacia una arquitectura distribuida, evitando la sobreingeniería y la complejidad prematura.

---

## 🏗️ **Arquitectura y Estado Actual**

La arquitectura de AEGEN está diseñada para evolucionar en fases claras.

### **Fase 1: El Monolito Inteligente y Resiliente (Completa)**

Actualmente, AEGEN opera como un sistema monolítico contenido en un único servicio Docker. Aunque es un monolito, está internamente desacoplado y es observable.

-   **API (FastAPI):** Recibe las peticiones y las publica como eventos en el bus.
-   **IEventBus (InMemoryEventBus):** Un bus de eventos en memoria (`asyncio.Queue`) que desacopla la recepción de la tarea de su procesamiento.
-   **Workers (Background Tasks):** Consumidores de eventos que se ejecutan como tareas de fondo dentro del mismo proceso de la API.
-   **WorkflowRegistry:** Permite el descubrimiento y la ejecución de flujos de trabajo de manera dinámica.
-   **Observabilidad "Día Cero":**
    -   **Logging Estructurado:** Todos los logs se emiten en formato JSON en producción.
    -   **ID de Correlación (`trace_id`):** Cada petición tiene un `trace_id` único que se propaga por todos los logs, permitiendo un seguimiento completo de la solicitud.

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

---

## 🗺️ **Próximos Pasos y Hoja de Ruta (Roadmap)**

Con la Fase 1 completada, los siguientes pasos se centran en la resiliencia y la preparación para la transición a un sistema distribuido.

1.  **Implementar Métricas con Prometheus (Paso 4):**
    -   **Acción:** Activar y configurar `prometheus-fastapi-instrumentator` en `main.py` para exponer métricas clave de la API (latencia, RPS, errores).
    -   **Objetivo:** Obtener visibilidad cuantitativa del rendimiento del sistema.

2.  **Añadir Resiliencia Básica (Paso 5):**
    -   **Acción:** Crear un decorador `@retry_on_failure` para los workflows, que implemente una lógica de reintentos con back-off exponencial.
    -   **Acción:** Implementar idempotencia básica en los workers usando el `task_id` del evento para evitar el procesamiento duplicado.
    -   **Objetivo:** Aumentar la robustez del sistema ante fallos transitorios.

3.  **Desarrollar el `MigrationDecisionEngine` (Paso 7 - Futuro):**
    -   **Acción:** Crear el motor que consumirá las métricas de Prometheus para decidir objetivamente cuándo es el momento de migrar a la Fase 2 (arquitectura distribuida con Redis).
    -   **Objetivo:** Automatizar las decisiones de escalado basadas en evidencia.

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
├── 🗂️ src/
│   ├── 📄 main.py                     # Punto de entrada de FastAPI y configuración
│   ├── 🗂️ agents/                    # Lógica de agentes y workflows
│   ├── 🗂️ api/                       # Endpoints de la API (Routers)
│   ├── 🗂️ core/                      # Núcleo de la aplicación
│   │   ├── 📄 dependencies.py
│   │   ├── 📄 error_handling.py
│   │   ├── 📄 exceptions.py
│   │   ├── 📄 logging_config.py
│   │   ├── 📄 middleware.py           # Middlewares (e.g., CorrelationId)
│   │   ├── 📄 registry.py             # WorkflowRegistry
│   │   ├── 📄 schemas.py
│   │   ├── 🗂️ bus/
│   │   └── 🗂️ interfaces/
│   ├── 🗂️ tools/
│   └── 🗂️ vector_db/
└── 🗂️ tests/
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

1.  **Clonar el repositorio y entrar al directorio.**
2.  **Configurar variables de entorno:** `cp .env.example .env`
3.  **Levantar los servicios:** `make up` o `docker-compose up -d --build`

### **Uso Básico**

-   **Documentación Interactiva:** [http://localhost:8000/docs](http://localhost:8000/docs)
-   **Endpoint de Análisis:**
    ```http
    POST http://localhost:8000/api/v1/analysis/
    Content-Type: application/json

    {
      "query": "Analiza los riesgos del protocolo Uniswap V4"
    }
    ```
    La API devolverá un `HTTP 202 Accepted` y un `X-Correlation-ID` en las cabeceras. Puedes usar este ID para rastrear la solicitud en los logs.

---
*Documentación viva del proyecto. Versión 1.1.0*
