# 🤖 AEGEN: Manual de Arquitectura y Desarrollo

**Versión del Documento: 2.1.0**

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
│   │       ├── __init__.py
│   │       ├── base_workflow.py
│   │       └── research/
│   │           ├── __init__.py
│   │           └── researcher.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── analysis.py
│   │       └── status.py
│   ├── core/
│   │   ├── __init__.py
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
│   │   ├── document_processing.py
│   │   ├── image_processing.py
│   │   ├── speech_processing.py
│   │   ├── documents/
│   │   │   └── process_documents.py
│   │   └── youtube/
│   │       └── youtube_tools.py
│   └── vector_db/
│       └── chroma_manager.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── integration/
    │   └── test_api_endpoints.py
    └── unit/
        └── test_schemas.py
```

### 3.2. Descripción Detallada de Componentes

- `src/main.py`: **Ensamblador de la Aplicación.** Punto de entrada de FastAPI. Su única responsabilidad es configurar y unir todos los componentes. **No debe contener lógica de negocio.**

- `src/core/interfaces/`: **Contratos de Comportamiento (ABCs).** El corazón del desacoplamiento. Define las interfaces (`IEventBus`, `IWorkflow`, `ITool`).

- `src/core/bus/`: **Implementaciones del Bus de Eventos.** Contiene las implementaciones concretas de `IEventBus`.

- `src/core/schemas.py`: **Contratos de Datos.** Define todos los modelos Pydantic para la validación de datos de la API y la estructura de los eventos.

- `src/api/routers/`: **Capa de API.** Expone los endpoints HTTP. Su única función es recibir, validar y publicar eventos. **No debe contener lógica de negocio.**

- `src/agents/workflows/`: **Cerebro de la Lógica de Negocio.** Orquesta la secuencia de pasos para completar una tarea. Aquí es donde se usa LangChain/LangGraph.

- `src/tools/`: **Caja de Herramientas.** Contiene funciones atómicas y reutilizables que realizan tareas específicas. Son invocadas por los workflows.

- `tests/`: **Garantía de Calidad.** Contiene las pruebas del sistema.

---

## 4. 🧪 Estrategia de Pruebas

La funcionalidad no se considera completa sin pruebas. Nuestro objetivo es mantener una cobertura de código superior al 85%.

- **Pruebas Unitarias (`tests/unit/`):**
  - **Qué probar:** Componentes aislados (Tools, Workflows con dependencias mockeadas, etc.).
  - **Objetivo:** Verificar que cada pieza de lógica funciona correctamente por sí sola.

- **Pruebas de Integración (`tests/integration/`):**
  - **Qué probar:** El flujo completo desde la API hasta el worker.
  - **Objetivo:** Asegurar que los componentes interactúan correctamente entre sí.

---

## 5. 🗺️ Hoja de Ruta (Roadmap)

### **Roadmap Funcional: Construcción de la Inteligencia (Prioridad Actual)**

1.  **Implementar el Workflow Orquestador:** Crear un `OrchestratorWorkflow` con LangGraph.
2.  **Desarrollar Herramientas (Tools) Base:** Implementar `SpeechToTextTool` y `ExcelWriterTool`.
3.  **Adaptar la API para Entradas Multimodales:** Modificar el endpoint de ingestión para manejar cargas de archivos.

### **Roadmap de Infraestructura: Evolución de la Plataforma (Futuro)**

1.  **Contenerización de Workers:** Actualizar `docker-compose.yml` para lanzar un servicio `worker` que use el target `worker` del `Dockerfile`.
2.  **Transición a Fase 2:** Activar el `RedisEventBus` y escalar el servicio `worker` cuando las métricas lo justifiquen.

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

_Documentación viva del proyecto. Versión 2.1.0_
