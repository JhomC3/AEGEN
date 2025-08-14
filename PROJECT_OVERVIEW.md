# AEGEN: El Playbook Constitucional

> **Versión:** 9.0 (Edición Post-Fase 1, "Gobernanza Ejecutable")
> **Estado:** Prescriptivo y Vinculante
> **Qué cambió en v9.0:** Adopción de una gobernanza ejecutable con artefactos normativos externos (`rules.md`, `PRD.md`), gates de CI verificables, y un roadmap por sprints con DoD claros. Se formaliza la seguridad, el control de costos y la gobernanza de prompts como pilares del proyecto.

**Preámbulo:** Este documento es la constitución del proyecto AEGEN y su única fuente de verdad. Se ramifica en documentos normativos adjuntos (`PRD.md`, `rules.md`) que detallan los requisitos de producto y las reglas técnicas. Su lectura y adhesión, junto con la de sus documentos adjuntos, son un prerrequisito para escribir una sola línea de código.

## 📖 1. La Doctrina: Filosofía y Principios de Diseño

La doctrina de AEGEN se basa en la **Arquitectura Evolutiva, Pragmática y Verificable**.

1.  **Gobernanza Ejecutable y Verificable:** Las reglas no son sugerencias, son leyes forzadas por la automatización (CI/CD, hooks). La disciplina se delega al sistema, no a la memoria del desarrollador.
2.  **Simplicidad Pragmática:** La complejidad solo se introduce si su Retorno de Inversión (ROI) es medible. Se empieza simple y se evoluciona hacia la complejidad solo cuando un requisito funcional lo exige explícitamente.
3.  **Evolución Guiada por Evidencia:** La transición entre fases arquitectónicas es detonada por el incumplimiento de umbrales cuantitativos. El `MigrationDecisionEngine` expone estas recomendaciones en `/system/status`, basándose en métricas reales (latencia, tasa de error, costo).
4.  **Seguridad y Costo por Diseño:** La seguridad no es un añadido, es un requisito. El costo no es un resultado, es una restricción. Ambos se consideran en cada decisión de diseño, con métricas y gates para su control.
5.  **Orquestación Basada en LangGraph:** La lógica de los agentes se modela como grafos de estado (`StateGraph`), proporcionando una estructura declarativa, observable y extensible.
6.  **LLM-First:** Cada componente debe ser fácil de entender, usar y testear por un modelo de lenguaje. La claridad, modularidad, contratos explícitos (`Pydantic`) y docstrings con `LLM-hints` son obligatorios.
7.  **Abstracción de Canales:** El núcleo de los agentes es agnóstico a la fuente de datos mediante **Adaptadores de Entrada** y un **Evento Canónico Interno** (`CanonicalEventV1`).

## 📜 2. La Ley: Jerarquía Normativa y Estándares Clave

Estas reglas son mandatorias y forzadas por herramientas automatizadas.

### 2.1. Jerarquía de Autoridad y Documentos Normativos

Los documentos del proyecto siguen una estricta jerarquía de precedencia. En caso de conflicto, el documento de mayor nivel prevalece. La integridad y coherencia entre ellos es validada automáticamente en CI mediante checksums.

1.  **`PROJECT_OVERVIEW.md` (Constitución - Este Documento):** Define la visión, principios, arquitectura y roadmap.
2.  **`PRD.md` (Product Requirements Document):** Define el QUÉ y el PORQUÉ. Personas, casos de uso, KPIs, requisitos no funcionales y DoD de negocio.
3.  **`rules.md` (Reglas Técnicas):** Define el CÓMO. Estándares de código, políticas de errores, seguridad, observabilidad y compatibilidad con severidad (Must/Should/May).
4.  **Código y Docstrings (`LLM-hints`):** La implementación final, que debe adherirse a todo lo anterior.
5.  **Issues / Pull Requests:** Unidades de trabajo que proponen cambios al código y documentos.

### 2.2. Estándares Fundamentales (Extracto de `rules.md`)

-   **Async I/O Obligatorio:** Toda operación de I/O DEBE ser `async`. Prohibido el uso de librerías síncronas como `requests`.
-   **Orquestación de Archivos:** Las `Tools` son puras y sin estado. El ciclo de vida de los archivos (creación/eliminación en directorios temporales) es responsabilidad del **orquestador** (ej. `webhooks.py`).
-   **Plantilla de Commit (Forzada por Git Hook):**
    ```
    feat(scope): resumen imperativo y conciso

    [BREAKING] # Opcional

    • WHY: El user-story o bug que resuelve (ref: TICKET-ID).
    • WHAT: La solución técnica a alto nivel.
    • HOW: Archivos clave modificados, si es relevante.
    ```
-   **Principio del Código de Referencia:** Antes de escribir código, busca un ejemplo en el directorio `playbooks/` como estándar mínimo.

## 🏗️ 3. El Blueprint: Arquitectura y Diagnóstico de Estado

**Leyenda de Estado:**
- ✅: Implementado y Validado
- 🎯: Foco Actual del Sprint
- 🚧: En Progreso
- ❌: No Implementado

```text
AEGEN/
├── Dockerfile                  # ✅ Configuración base robusta.
├── compose.yml                 # ✅ Sin cambios.
├── makefile                    # 🚧 A expandir con 'make verify' y más.
├── pyproject.toml              # 🚧 A actualizar con dependencias (LangChain, etc.).
├── PROJECT_OVERVIEW.md         # 📍 ESTE DOCUMENTO.
├── PRD.md                      # 🎯 Documento de requisitos de producto.
├── rules.md                    # 🎯 Reglas técnicas con severidad (Must/Should/May).
├── OWNERS.md                   # 🎯 Propietarios de código por directorio.
├── CHANGELOG.md                # 🚧 Generado automáticamente desde Conventional Commits.
├── adr/                        # 🚧 Architectural Decision Records (ej: ADR-0001-langgraph).
│   └── adr_template.md
├── playbooks/                  # 🎯 Guías ejecutables (ej: añadir_tool.md).
│   └── ...
├── prompts/                    # 🎯 Prompts versionados, con snapshots y changelog.
│   ├── transcription_agent/
│   │   └── v1.yaml
│   └── CHANGELOG.md
└── src/
    ├── main.py                 # ✅ Routers configurados.
    ├── api/
    │   └── routers/
    │       └── webhooks.py     # ✅ Refactorizado para robustez con temp files.
    ├── core/
    │   ├── schemas.py          # 🎯 A definir CanonicalEventV1 y GraphStateV1.
    │   └── ...
    ├── agents/                 # 🧠 Lógica de orquestación basada en LangGraph.
    │   ├── orchestrator.py     # 🎯 El MasterRouter dinámico que descubre especialistas.
    │   └── specialists/
    │       └── transcription_agent.py # ✅ Agente agnóstico implementado.
    └── tools/                  # 🛠️ Funciones atómicas, envueltas con @tool.
        ├── speech_processing.py  # ✅ Adaptado con @tool.
        └── ...
└── tests/                      # 🚧 En progreso.
    ├── prompts/                # 🎯 Snapshot tests para prompts.
    │   └── test_transcription_snapshot.py
    ├── rag_eval/               # 🎯 Dataset canónico y script de evaluación para RAG.
    │   ├── questions.csv
    │   └── eval.py
    └── audio_samples/          # ✅ Muestras de audio para tests de transcripción.
```

## 🧪 4. La Garantía: Estrategia de Testing Holístico

**Diagnóstico:** La falta de pruebas es una emergencia técnica. La estrategia se expande para cubrir la naturaleza de un sistema LLM-first. La cobertura mínima global es del 85% (branches), forzada por CI.

| Capa                                 | Tooling Mínimo                        | Cobertura Mínima                  |
| :----------------------------------- | :------------------------------------ | :-------------------------------- |
| **Unit (puro)**                      | `pytest`, `factory-boy`               | 90% (branches)                    |
| **Integration**                      | `httpx.AsyncClient`, `respx`          | 85% (branches)                    |
| **Contract (API & Schemas)**         | `schemathesis` (smoke), `pydantic`    | 100% de validez de contratos      |
| **Prompt (Semántica)**               | `pytest` (Snapshot Testing)           | 100% de prompts críticos cubiertos |
| **Calidad de Modelo (RAG/Agente)**   | Scripts de evaluación custom         | Superar umbrales en dataset canónico |
| **Seguridad (Estática)**             | `bandit`, `gitleaks`, `ruff`          | 0 issues de alta severidad        |
| **Mutation (gating)**                | `mutmut` (en archivos cambiados)      | < 3% de mutantes sobreviven       |

## 🗺️ 5. Roadmap

El roadmap se estructura en Sprints con Entregables (Deliverables) y Definición de Hecho (DoD) verificables.

#### ✅ FASE 1: AGENTE DE TRANSCRIPCIÓN END-TO-END (Completada)

- **Resultado:** **Éxito.** El flujo de transcripción funciona de manera robusta y limpia.

#### ✅ FASE 2: GOBERNANZA FUNDACIONAL Y ENABLER MVP (Completada)

-   **Resultado:** **Éxito.** Se ha construido el "sistema operativo" del proyecto. El desarrollo futuro se regirá por una gobernanza clara, verificable y automatizada.

#### 🎯 FASE 3: CONSOLIDACIÓN DEL MVP DE AGENTES (Foco Actual)

-   **Meta:** Evolucionar de un servicio de una sola función a una plataforma de agentes conversacionales con estado, capaz de orquestar múltiples especialistas y mantener el contexto de una conversación.
-   **Entregables Clave:**
    1.  **`MasterRouter` Implementado:**
        -   **Qué:** Un grafo de LangGraph en `src/agents/orchestrator.py` que actúa como el cerebro central del sistema.
        -   **Cómo:** Utiliza un LLM para analizar la intención del usuario a partir del `CanonicalEventV1` y enruta la tarea al agente especialista apropiado (`TranscriptionAgent`, `InventoryAgent`, etc.).
    2.  **Memoria de Sesión con Redis:**
        -   **Qué:** La capacidad del sistema para recordar el contexto de una conversación a lo largo de múltiples interacciones con un mismo usuario.
        -   **Cómo:** El `GraphStateV1` de cada `chat_id` se persiste en Redis. Antes de ejecutar el `MasterRouter`, se carga el estado de la sesión; después de la ejecución, se guarda el estado actualizado.
    3.  **`InventoryAgent` (Primer Especialista con Estado):**
        -   **Qué:** Un nuevo agente especialista que puede entender instrucciones para modificar un archivo (ej. un Excel de inventario) a lo largo de una conversación.
        -   **Cómo:** Se crearán nuevas herramientas atómicas para la manipulación de archivos de hojas de cálculo. El `InventoryAgent` utilizará estas herramientas y la memoria de sesión para realizar tareas complejas de varios pasos.
    4.  **Integración E2E:** El `webhook` de la API se modifica para invocar al `MasterRouter` en lugar de a un agente específico, completando el nuevo flujo de procesamiento.
-   **DoD (Definition of Done):** Un usuario puede iniciar una conversación, ser enrutado al `InventoryAgent`, subir un archivo Excel, y en una interacción posterior, enviar un audio o texto para actualizar dicho archivo. El sistema debe mantener el contexto del archivo entre interacciones.

#### FASE 4: EXPANSIÓN DE LA FEDERACIÓN Y LA PLATAFORMA (Visión a Futuro)

-   **Meta:** Añadir más agentes y enriquecer la plataforma con memoria a largo plazo, colas de tareas y optimización de costos avanzada.

## 🚀 6. La Cabina: Guía de Operaciones y Desarrollo

Comandos únicos para una experiencia de desarrollo consistente.

```bash
# Iniciar entorno de desarrollo completo con hot-reload
make dev

# Ejecutar la suite de verificación completa (lint, tipos, tests, seguridad)
# Este es el comando que ejecuta CI antes de permitir un merge.
# Nota: Si falla por problemas de formato, ejecuta 'make format' para arreglarlos.
make verify

# Generar y validar documentación de la API
make docs
```

**Endpoints Clave (local):**

-   **Swagger UI:** `http://localhost:8000/docs`
-   **Métricas (Prometheus):** `http://localhost:8000/metrics`
-   **Estado del Sistema:** `http://localhost:8000/system/status` (incluye versiones de documentos, checksums y recomendación del `MigrationDecisionEngine`).

## 🔧 7. Guía de Contribución (Humano & LLM-First)

### **Ciclo de Vida de una Funcionalidad (Flujo de Git Mandatorio)**

#### **El Protocolo de Sincronización Obligatoria (PSO)**

**Directiva de Prioridad del Usuario:** La instrucción explícita y actual del usuario tiene la máxima prioridad. Este protocolo puede ser simplificado, modificado o completamente omitido si el usuario así lo indica directamente. El objetivo es la asistencia eficiente, no la adherencia ciega a un proceso. En ausencia de una instrucción contraria, se seguirá el siguiente procedimiento por defecto.

Este protocolo es un **gate de gobernanza** y se activa al inicio de cualquier nueva tarea de desarrollo, corrección o refactorización. Reemplaza al anterior "Paso 0" con un proceso algorítmico estricto.

**Paso 1: Declaración de Intención y Plan Documental**
- Antes de cualquier otra acción, se debe declarar el entendimiento de la tarea y presentar un **Plan Documental**.
- Este plan listará explícitamente **todos los archivos de documentación** que necesitan ser creados o modificados para reflejar el cambio propuesto. La revisión debe incluir, como mínimo:
    1.  **Contexto Estratégico (`¿Para dónde vamos?`):** `PROJECT_OVERVIEW.md`
    2.  **Contexto de Producto (`¿Qué construimos?`):** `PRD.md`
    3.  **Contexto Técnico (`¿Cómo lo construimos?`):** `rules.md` y `adr/`
    4.  **Contexto Real (`¿Dónde estamos?`):** Inspección de la estructura de archivos actual.
    5.  **Contexto de Ejecución (`¿Cómo funciona?`):** `Dockerfile`, `compose.yml`, `makefile`.

**Paso 2: Ejecución de Cambios Documentales**
- Se procederá a ejecutar **únicamente** los cambios descritos en el Plan Documental.
- **No se escribirá ni modificará ningún archivo de código fuente (`.py`) en este paso.**

**Paso 3: Solicitud de Aprobación (El "Gate" de Gobernanza)**
- Una vez completadas todas las modificaciones documentales, el proceso se detendrá.
- Se finalizará la respuesta con la pregunta explícita: **"La documentación ha sido actualizada y alineada. ¿Apruebas este plan y me autorizas a proceder con la implementación del código?"**

**Paso 4: Inicio de la Implementación del Código**
- **Solo y exclusivamente si se recibe una aprobación explícita**, se comenzará a escribir o modificar el código fuente para implementar la tarea.
- Si no hay aprobación o se solicitan más cambios, el proceso vuelve al Paso 1.

**Pasos 1-4: Ciclo de Git (Sin cambios)**
Sigue el ciclo estándar: `checkout develop -> pull -> checkout -b feature/... -> develop -> push -> PR`.

### **Checklist Pre-Merge (Forzada por CI y plantilla de PR)**

Un PR no será fusionado a menos que cumpla con TODOS los siguientes puntos:

1.  ✅ `make verify` pasa sin errores.
2.  ✅ La plantilla de Pull Request está completamente rellenada.
3.  ✅ **Cambios de Contrato:** Si se modifica un schema o endpoint, la versión se ha incrementado y se ha añadido una nota de migración.
4.  ✅ **Cambios en Prompts:** Si se modifica un prompt, su snapshot test se ha actualizado y `prompts/CHANGELOG.md` documenta el cambio.
5.  ✅ **Decisiones de Arquitectura:** Si se toma una decisión de alto impacto, se ha creado o actualizado un `ADR`.
6.  ✅ **Dependencia en `OWNERS.md`:** El PR ha sido aprobado por al menos un propietario del código modificado.
7.  ✅ **Alineamiento con Documentos:** El cambio es consistente con `PROJECT_OVERVIEW.md`, `PRD.md` y `rules.md`. Si no lo es, el PR debe incluir también la actualización de dichos documentos.

---

## Anexo A: Artefactos de Gobernanza a Crear (Contenido Mínimo)

### `PRD.md` (v0.1)

```markdown
# AEGEN - Product Requirements Document
> Version: 0.1.0; Estado: Prescriptivo; Owner: Product/Tech

## 1. Visión
Entregar respuestas precisas y rápidas a los usuarios a través de una plataforma de agentes federados, comenzando con transcripción y consulta de documentos.

## 2. Flujos y KPIs (Fase 2)
- **Transcripción:** p95 latencia < 2s; Word Error Rate (WER) no debe degradarse respecto a la línea base en `audio_samples/`.
- **RAG QA:** p95 latencia < 3s; `groundedness` (basado en citas) >= 0.9; `recall@3` >= 0.85 en `rag_eval/`.

## 3. Requisitos No Funcionales (NFRs)
- **Timeouts:** Timeout global por request de 30s.
- **Límites:** Tamaño máximo de archivo de audio de 25MB.
- **Costo:** Monitoreo del costo por 1k requests por flujo.

## 4. Fuera de Alcance (Fase 2)
- Memoria conversacional a largo plazo.
- Múltiples fuentes de datos para RAG.
```

### `rules.md` (v0.1)

```markdown
# AEGEN - Reglas Técnicas
> Version: 0.1.0; Estado: Prescriptivo; Owner: Tech

## Severidad: MUST (Obligatorio, Forzado por CI), SHOULD (Recomendado), MAY (Opcional)

## 1. Código y Dependencias
- **[MUST]** Todo I/O debe ser `async`.
- **[MUST]** No se permiten secretos hardcodeados. Usar Pydantic Settings para cargar desde el entorno.
- **[MUST]** Logging debe ser JSON estructurado y contener un `correlation_id`.
- **[MUST]** No se debe registrar información PII. Usar un redactor para campos sensibles.

## 2. Diseño de Componentes
- **[MUST]** Las `Tools` deben ser sin estado y no gestionar el ciclo de vida de archivos.
- **[MUST]** Toda interfaz pública debe tener tipado estricto. `Any` solo con `TODO: [TICKET-ID]`.
- **[MUST]** Todo método/función pública debe tener un docstring con formato Numpy/Google y `LLM-hints`.

## 3. Testing y Calidad
- **[MUST]** Todo PR debe incluir tests para la nueva funcionalidad.
- **[MUST]** La cobertura de pruebas no puede disminuir.
- **[MUST]** Todo prompt en `prompts/` debe tener un test de snapshot.

## 4. Política de Errores
- **[SHOULD]** Usar la taxonomía de errores definida (`UserError`, `ToolError`, `TransientError`).
- **[SHOULD]** Implementar reintentos con backoff exponencial y jitter para errores transitorios.
```

### VEREDICTO FINAL

Este documento, en su versión 9.0, es el resultado de una síntesis estratégica y establece un sistema operativo ejecutable, verificable y pragmático. **Se adopta este documento y sus artefactos adjuntos como la constitución para todo el trabajo a continuación.**
