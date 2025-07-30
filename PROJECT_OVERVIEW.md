# 🤖 AEGEN: Manual de Arquitectura y Desarrollo

**Versión del Documento: 2.0.0**

> **Nota del Arquitecto:** Este documento es la **fuente de verdad** y la **constitución** del proyecto AEGEN. Todo desarrollador (humano o IA) que contribuya a este proyecto debe leer, entender y adherirse a los principios y convenciones aquí descritos. El código que no siga estas directrices no será aceptado.

## 1. 📖 Filosofía de Desarrollo

La filosofía central es la **Arquitectura Evolutiva y Pragmática**. No construimos para un futuro hipotético; construimos un sistema simple y funcional hoy, con las bases adecuadas para que pueda evolucionar de manera controlada y basada en evidencia.

- **Simplicidad Primero:** Siempre optamos por la solución más simple y legible.
- **Evolución Basada en Evidencia:** No optimizamos prematuramente. La transición de una fase arquitectónica a otra solo se realizará cuando las métricas de rendimiento lo justifiquen.
- **Desacoplamiento Interno:** Los componentes deben depender de abstracciones (interfaces), no de implementaciones concretas.

---

## 2. 📜 Estándares y Convenciones

Estas reglas son mandatorias para mantener la coherencia y calidad del proyecto.

### 2.1. Lenguaje y Formato
- **Idioma del Código:** El código (nombres de variables, funciones, clases, etc.) se escribe **exclusivamente en inglés**.
- **Idioma de la Documentación:** Los comentarios, docstrings y documentos como este se escriben **en español**.
- **Formato de Código:** Gestionado automáticamente por `black` y `ruff` vía pre-commit.

### 2.2. Estándares de Logging
- **Prohibido `print()`:** Se debe usar el módulo `logging` para toda salida informativa.
- **Logging Estructurado:** La configuración ya emite logs en JSON en producción.
- **Trazabilidad (`trace_id`):** El `CorrelationIdMiddleware` asegura que cada log contenga un `trace_id`.

### 2.3. Docstrings y Comentarios
- **Formato de Docstrings:** Se utilizará el **estilo Google**.
- **Filosofía de Comentarios:** Los comentarios explican el **"porqué"**, no el "qué".

---

## 3. 🏗️ Guía de Arquitectura y Estructura de Directorios

AEGEN utiliza una arquitectura limpia y desacoplada. Es mandatorio respetar la responsabilidad de cada componente.

### 3.1. Árbol de Directorios Completo

```
AEGEN/
├── Dockerfile
├── README.md
├── PROJECT_OVERVIEW.md
├── compose.yml
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   └── workflows/
│   │       ├── base_workflow.py
│   │       └── research/
│   │           └── researcher.py
│   ├── api/
│   │   └── routers/
│   │       ├── analysis.py
│   │       └── status.py
│   ├── core/
│   │   ├── bus/
│   │   │   ├── in_memory.py
│   │   │   └── redis.py
│   │   ├── config/
│   │   │   ├── base.py
│   │   │   └── ...
│   │   ├── interfaces/
│   │   │   ├── bus.py
│   │   │   ├── tool.py
│   │   │   └── workflow.py
│   │   ├── dependencies.py
│   │   ├── engine.py
│   │   ├── logging_config.py
│   │   ├── middleware.py
│   │   ├── registry.py
│   │   └── schemas.py
│   ├── tools/
│   │   ├── documents/
│   │   └── youtube/
│   └── vector_db/
│       └── chroma_manager.py
└── tests/
    ├── conftest.py
    ├── integration/
    │   └── test_api_endpoints.py
    └── unit/
        └── test_schemas.py
```

### 3.2. Descripción Detallada de Componentes

- `src/main.py`: **Ensamblador de la Aplicación.** Punto de entrada de FastAPI. Su única responsabilidad es configurar y unir todos los componentes: `lifespan`, middlewares, routers, etc. **No debe contener lógica de negocio.**

- `src/core/interfaces/`: **Contratos de Comportamiento (ABCs).** El corazón del desacoplamiento. Define las interfaces (`IEventBus`, `IWorkflow`, `ITool`) que garantizan que los componentes sean intercambiables.

- `src/core/bus/`: **Implementaciones del Bus de Eventos.** Contiene las implementaciones concretas de `IEventBus` (`in_memory.py`, `redis.py`).

- `src/core/schemas.py`: **Contratos de Datos.** Define todos los modelos Pydantic para la validación de datos de la API y la estructura de los eventos. **Toda estructura de datos compartida debe definirse aquí.**

- `src/api/routers/`: **Capa de API.** Expone los endpoints HTTP. Su única función es: 1) Recibir peticiones, 2) Validarlas con un esquema de `schemas.py`, 3) Publicar un evento en el `IEventBus`. **No debe contener lógica de negocio.**

- `src/agents/workflows/`: **Cerebro de la Lógica de Negocio.** Orquesta la secuencia de pasos para completar una tarea. Aquí es donde se usa LangChain/LangGraph para crear agentes que razonan y planifican.

- `src/tools/`: **Caja de Herramientas.** Contiene funciones atómicas y reutilizables que realizan tareas específicas (ej. `transcribir_audio`, `buscar_en_la_web`). Son invocadas por los workflows. **No deben contener lógica de orquestación.**

- `tests/`: **Garantía de Calidad.** Contiene las pruebas del sistema. Ver la sección de Estrategia de Pruebas.

---

## 4. 🧪 Estrategia de Pruebas

La funcionalidad no se considera completa sin pruebas. Nuestro objetivo es mantener una cobertura de código superior al 85%.

- **Pruebas Unitarias (`tests/unit/`):**
  - **Qué probar:** Componentes aislados. Probar una `Tool` individualmente, un `Workflow` con `Tools` mockeadas, o la lógica de un `schema`.
  - **Objetivo:** Verificar que cada pieza de lógica funciona correctamente por sí sola.

- **Pruebas de Integración (`tests/integration/`):**
  - **Qué probar:** El flujo completo desde la API hasta el worker. Se prueba que al llamar a un endpoint, se publica el evento correcto y el `WorkflowCoordinator` lo procesa.
  - **Objetivo:** Asegurar que los componentes interactúan correctamente entre sí.

---

## 5. 🗺️ Hoja de Ruta (Roadmap)

### **Roadmap Funcional: Construcción de la Inteligencia (Prioridad Actual)**

1.  **Implementar el Workflow Orquestador:** Crear un `OrchestratorWorkflow` con LangGraph para interpretar y planificar la ejecución de peticiones en lenguaje natural.
2.  **Desarrollar Herramientas (Tools) Base:** Implementar `SpeechToTextTool` y `ExcelWriterTool`.
3.  **Adaptar la API para Entradas Multimodales:** Modificar el endpoint de ingestión para manejar cargas de archivos.

### **Roadmap de Infraestructura: Evolución de la Plataforma (Futuro)**

1.  **Contenerización de Workers:** El `Dockerfile` ya está preparado con un target `worker`. El siguiente paso es actualizar `docker-compose.yml` para lanzar un servicio `worker` que use este target, permitiendo el escalado independiente.
2.  **Transición a Fase 2:** Cuando las métricas lo justifiquen, se activará el `RedisEventBus` en la configuración y se escalará el servicio `worker` en `docker-compose.yml`.

---

## 6. 🚀 Inicio Rápido y Uso

### Prerrequisitos
- Docker y Docker Compose

### Instalación y Ejecución
1.  **Clonar el repositorio:** `git clone https://github.com/JhomC3/aegen.git && cd aegen`
2.  **Configurar entorno:** `cp .env.example .env`
3.  **Levantar servicios:** `make up` (o `docker-compose up -d --build`)

### Uso Básico
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Métricas:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Endpoint de Análisis:** Envía una petición a `/api/v1/analysis/ingest` para iniciar un flujo de trabajo.

---

_Documentación viva del proyecto. Versión 2.0.0_
