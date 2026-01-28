# AEGEN: Plataforma de Orquestación de Agentes Multi-Especialistas

> **MAGI:** El Asistente Conversacional (Interfaz Principal)
> **Versión:** 0.2.0 (Diskless Architecture)
> **Estado:** Arquitectura Diskless Implementada
> **Branch Actual:** `main`

<!-- LLM-Hint: AEGEN es la infraestructura. MAGI es el agente conversacional que el usuario ve. MAGI utiliza el MasterOrchestrator para delegar tareas a especialistas como el Agente TCC. Este documento es la Fuente de Verdad. -->

## 🎯 Contexto Actual del Proyecto

### Estado Real
El estado del proyecto se gestiona automáticamente a través de issues y milestones en GitHub/GitLab.
Para ver el estado actual del sistema, ejecutar: `make status`

## 📖 1. Filosofía de Desarrollo

### Principios Core (Inmutables)
1. **Arquitectura Evolutiva:** De monolito funcional → sistema distribuido cuando las métricas lo justifiquen
2. **Pragmatismo Medible:** Complejidad solo si ROI > umbral definido
3. **Gobernanza Automática:** Las reglas se ejecutan, no se recuerdan
4. **LLM-First:** Diseñado para ser usado y entendido por IA
5. **Observabilidad Native:** Métricas y trazas desde día 1

### Patrones de Diseño
- **Event-Driven:** `CanonicalEventV1` como lingua franca
- **Registry Pattern:** Autodescubrimiento de especialistas
- **State Graphs:** LangGraph para orquestación declarativa
- **Tool Composition:** Herramientas atómicas y componibles

## 📜 2. La Ley: Jerarquía Normativa y Estándares Clave

Estas reglas son mandatorias y forzadas por herramientas automatizadas.

### 2.1. Jerarquía de Autoridad y Documentos Normativos

1.  **`PROJECT_OVERVIEW.md` (Constitución - Este Documento):** Define la visión, principios, arquitectura y roadmap.
2.  **`rules.md` (Reglas Técnicas):** Define el CÓMO. Estándares de código, políticas de errores, seguridad, observabilidad y compatibilidad con severidad (Must/Should/May).
3.  **`adr/` (Architecture Decision Records):** Decisiones arquitectónicas con contexto y justificación histórica.
4.  **Código y Docstrings (`LLM-hints`):** La implementación final, que debe adherirse a todo lo anterior.
5.  **Issues / Pull Requests:** Unidades de trabajo que proponen cambios al código y documentos.

### 2.2. Estándares Fundamentales (Extracto de `rules.md`)

-   **Async I/O Obligatorio:** Toda operación de I/O DEBE ser `async`.
-   **Orquestación de Archivos:** Las `Tools` son puras y sin estado.
-   **Plantilla de Commit (Forzada por Git Hook):** `feat(scope): resumen imperativo`
-   **Principio del Código de Referencia:** Antes de escribir código, busca un ejemplo en el directorio `playbooks/`.
-   **🚨 REVISAR CONTEXTO PRIMERO:** Antes de escribir código, crear archivos o carpetas, SIEMPRE revisar primero qué ya existe.
-   **🏗️ ARCHITECTURE FIRST:** MANDATORIO usar `.architecture/pre-code-checklist.md` antes de cualquier código.

## 🏗️ 2. Arquitectura Actual

### Componentes Implementados
```
MAGI/
├── 🎯 Punto de Entrada
│   ├── main.py              # ✅ FastAPI + middleware
│   └── api/routers/         # ✅ Webhooks, status, analysis
│
├── 🧠 Orquestación
│   ├── agents/
│   │   ├── orchestrator/    # ✅ MasterOrchestrator, GraphBuilder, Router
│   │   └── specialists/     # ✅ TCC, Chat, Transcription, etc.
│   │
│   ├── personality/         # ✅ NUEVO: Sistema de Personalidad Adaptativa
│   │   ├── base/            # ✅ SOUL.md, IDENTITY.md
│   │   ├── skills/          # ✅ Overlays (TCC, Chat)
│   │   └── prompt_builder.py # ✅ Composición dinámica
│   │
│   └── core/                # ✅ Schemas, Registry, Interfaces
│
├── 🛠️ Herramientas          # ✅ Speech, Telegram, Docs
│
└── 📊 Observabilidad        # ✅ Logging, Middleware, Metrics
```

### Flujo de Datos Actual (Arquitectura Diskless)
```mermaid
graph TD
    A[Telegram] --> B(Webhook);
    B --> C{CanonicalEventV1};
    C --> D[MasterOrchestrator];
    D --> E{EnhancedFunctionCallingRouter};
    E --> F[RoutingAnalyzer];
    F --> G{LLM (Gemini)};
    E --> H[Specialist Agent];
    H --> I[GraphExecution];
    I --> J[RedisMessageBuffer];
    J --> K[ConsolidationManager];
    K --> L[Google File Search API];
    I --> M(Response);
    M --> A;

    subgraph Memory
        J
        K
        L
        N[Redis Profile Cache]
    end
```

## 🧪 3. Estrategia de Testing (Gradual)

### Métricas por Fase
| Fase | Unit Coverage | Integration | Herramientas |
|------|---------------|-------------|--------------|
| **3A (Actual)** | 60% | 40% | pytest, respx |
| **3B (Q1)** | 75% | 60% | + snapshot testing |
| **3C (Q2)** | 85% | 75% | + contract testing |
| **Producción** | 90% | 85% | + mutation testing |

## 🗺️ 4. Roadmap Ejecutivo

### ✅ FASE 3A: MasterRouter Básico (COMPLETADA)
**Objetivo:** Enrutamiento funcional sin LLM. DoD Alcanzado.

### ✅ FASE 3B: Sistema Conversacional + Memoria (COMPLETADA)
**Objetivo:** Sistema conversacional completo con memoria persistente. DoD Alcanzado.

### ✅ FASE 3C: Arquitectura Diskless + Especialista TCC (COMPLETADA)
**Objetivo:** Eliminar dependencia de storage local + Especialista TCC funcional con memoria a largo plazo en Google Cloud.
- **Diskless Memory:** Implementado con Redis + Google File Search.
- **Multi-tenant Profiles:** Stateless ProfileManager operativo.
- **TCC Agent:** Integrado con búsqueda semántica de historial.

### 🌟 FASE 4: Federación Completa (Q2)
- Múltiples especialistas con LangSmith observability.
- Enrutamiento inteligente por LLM.

## 🚀 5. Guía de Desarrollo

### Comandos Esenciales
```bash
make dev          # Docker + hot-reload
make verify       # CI completa (lint + test + security)
make status       # Estado del proyecto
make doctor       # Diagnóstico
```

### Flujo Git/GitHub
- **main:** Releases estables.
- **develop:** Integration branch.
- **feature/*:** Development.

## 🔧 7. Herramientas de Contexto

- **API Docs:** http://localhost:8000/docs
- **Metrics:** http://localhost:8000/metrics
- **Status:** http://localhost:8000/system/status

---
**🚀 Este documento es la fuente de verdad del proyecto.**
