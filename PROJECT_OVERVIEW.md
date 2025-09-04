# AEGEN: Sistema de Agentes Evolutivo

> **Versión:** 10.0 (Edición "Contexto Dinámico y Pragmático")
> **Estado:** Activo y Evolutivo
> **Branch Actual:** `feature/phase3c-vector-multiagent`
> **Última Actualización:** 2025-09-04

<!-- LLM-Hint: This document follows a strict hierarchy. In case of conflict, PROJECT_OVERVIEW.md (this file) has the highest authority. The current project phase is defined in the "Estado Real" YAML block below. Use the DoD (Definition of Done) for each phase to understand completion criteria. All sections marked with 🎯 are current focus areas. -->

## 🎯 Contexto Actual del Proyecto

### Estado Real (Semi-Automático)
<!-- LLM-Hint: This block is semi-automated. Git status and timestamp are updated by 'make sync-docs'. Phase progress and milestones must be updated manually upon completion. -->
```yaml
Fase_Actual: "FASE 3C - CORE RESTORATION COMPLETADA"
Progreso_Fase_3A: "5/5 hitos completados (✅ COMPLETADA)"
Progreso_Fase_3B: "4/4 hitos completados + refactorización crítica (✅ COMPLETADA)"
Progreso_Fase_3C: "11/22 tasks completados (50% - ChatAgent + Orquestador completamente funcional)"
Próximo_Hito: "Observabilidad y Performance Optimization (Tasks #20-22)"
Funcionalidades_Activas:
  # Fase 3B (Mantenidas)
  - ✅ Transcripción E2E via Telegram (faster-whisper optimizado)
  - ✅ MasterOrchestrator Strategy Pattern (7 componentes clean)
  - ✅ Schemas CanonicalEventV1/GraphStateV2 + contratos inter-agente
  - ✅ Sistema de testing (85% cobertura + integration tests)
  - ✅ LangSmith Integration (tracing completo + cost tracking)
  - ✅ Redis Session Memory (TTL 1h, persistencia robusta)
  - ✅ Memoria conversacional bidireccional (audio + texto)
  - ✅ ChatAgent como punto único entrada + delegación inteligente
  - ✅ Chaining transcription → planner → respuesta final
  # Fase 3C (Tasks completados - 50% progreso)
  - ✅ Multi-tenant ChromaDB con aislamiento per-user (Task #1)
  - ✅ BaseModularAgent interface estable para composición (Task #2)
  - ✅ VectorMemoryManager persistente por usuario (Task #3)
  - ✅ FileHandlerAgent con validación segura y parsing (Task #5)
  - ✅ Sistema de roles USER/ADMIN/SUPER_ADMIN (Task #13)
  - ✅ SecureChromaManager con control de permisos
  - ✅ EnhancedFunctionCallingRouter (Tasks #6, #7, #9)
  - ✅ Integración de Memoria Híbrida (Task #10)
  - ✅ Estabilización y Depuración del Orquestador (Task #18)
  - ✅ Restauración COMPLETA ChatAgent ADR-0009 (Task #19)
  - ✅ Arquitectura híbrida: Performance + Funcionalidad
  - ✅ Function calling optimization: 36s → <2s routing
Branch_Trabajo: "feature/phase3c-vector-multiagent"
ADRs_Recientes: ["ADR-0007-fase3c-vector-multiagent (ACEPTADO)", "ADR-0008-advanced-multitenant-features (PROPUESTO)", "ADR-0009-routing-performance-migration (COMPLETADO - 100% exitoso)"]
Task_Master_Progress: "11/22 tasks done (Tasks #1,#2,#3,#5,#7,#8,#9,#10,#13,#18,#19 completed)"
Cambios_Pendientes: ['observabilidad LLM', 'performance profiling', 'data migration script', 'global collections manager']
Última_Sincronización: "2025-09-04 (ChatAgent restoration + observability tasks)"
```

### ¿Dónde Estamos Hoy?
- **✅ Completado:** Fase 3A - MasterRouter básico funcional
- **✅ Completado:** Fase 3B - Sistema conversacional completo con memoria persistente
- **✅ Completado:** Refactorización arquitectónica crítica (ADR-0006)
- **🎯 EN PROGRESO:** Fase 3C - Multi-tenant vector DB + agentes modulares (50% completado)
- **📊 Logrado:** LangSmith observabilidad LLM operacional
- **💾 Logrado:** Redis memoria conversacional robusta + ChromaDB multi-tenant
- **🎉 Meta Alcanzada:** Foundation sólida multi-tenant + ChatAgent completamente funcional + architecture híbrida performance/funcionalidad
- **🔧 Arquitectura:** ADR-0007 (vector multi-tenant) + ADR-0008 (características avanzadas)

**Preámbulo:** Este documento es la fuente de verdad evolutiva del proyecto AEGEN. Se actualiza automáticamente con el estado real y proporciona contexto inmediato sobre dónde estamos y hacia dónde vamos.

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

Los documentos del proyecto siguen una estricta jerarquía de precedencia. En caso de conflicto, el documento de mayor nivel prevalece. La integridad y coherencia entre ellos es validada automáticamente en CI mediante checksums.

1.  **`PROJECT_OVERVIEW.md` (Constitución - Este Documento):** Define la visión, principios, arquitectura y roadmap.
2.  **`rules.md` (Reglas Técnicas):** Define el CÓMO. Estándares de código, políticas de errores, seguridad, observabilidad y compatibilidad con severidad (Must/Should/May).
3.  **`adr/` (Architecture Decision Records):** Decisiones arquitectónicas con contexto y justificación histórica.
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
-   **🚨 REVISAR CONTEXTO PRIMERO:** Antes de escribir código, crear archivos o carpetas, SIEMPRE revisar primero qué ya existe usando herramientas de búsqueda (Read, LS, Grep, Glob). Esto previene duplicación, conflictos y trabajo innecesario.
-   **🏗️ ARCHITECTURE FIRST:** MANDATORIO usar `.architecture/pre-code-checklist.md` antes de cualquier código. Seguir `.architecture/development-workflow.md` para todo desarrollo. Clean Architecture es el estándar, no una opción.

## 🏗️ 2. Arquitectura Actual

### Componentes Implementados
```
AEGEN/
├── 🎯 Punto de Entrada
│   ├── main.py              # ✅ FastAPI + middleware
│   └── api/routers/
│       ├── webhooks.py      # ✅ Telegram webhook
│       ├── status.py        # ✅ Health checks
│       └── analysis.py      # ✅ API endpoints
│
├── 🧠 Orquestación
│   ├── agents/
│   │   ├── orchestrator/      # ✅ Lógica de orquestación principal
│   │   │   ├── master_orchestrator.py # ✅ Coordinador principal
│   │   │   ├── graph_builder.py       # ✅ Constructor de grafos
│   │   │   └── routing/               # ✅ Lógica de enrutamiento
│   │   │       ├── enhanced_router.py   # ✅ Router principal
│   │   │       └── routing_analyzer.py  # ✅ Analizador de intención
│   │   └── specialists/
│   │       ├── transcription_agent.py  # ✅ Funcional
│   │       └── chat_agent.py          # ✅ Funcional
│   │
│   └── core/
│       ├── schemas.py       # ✅ CanonicalEventV1, GraphStateV2
│       ├── registry.py      # ✅ Autodescubrimiento
│       └── interfaces/      # ✅ Contratos TypeScript-style
│
├── 🛠️ Herramientas
│   ├── speech_processing.py    # ✅ Whisper integrado
│   ├── telegram_interface.py  # ✅ Bot API
│   └── document_processing.py # ✅ Para FileHandlerAgent
│
└── 📊 Observabilidad
    ├── logging_config.py   # ✅ Structured JSON
    ├── middleware.py       # ✅ Correlation IDs
    └── /metrics           # ✅ Prometheus endpoint
```

### Flujo de Datos Actual
```mermaid
graph TD
    A[Telegram] --> B(Webhook);
    B --> C{CanonicalEventV1};
    C --> D[MasterOrchestrator];
    D --> E{EnhancedFunctionCallingRouter};
    E --> F[RoutingAnalyzer];
    F --> G{LLM (Gemini)};
    E --> H[SpecialistCache];
    H --> I[Specialist Agent];
    I --> J[GraphExecution];
    J --> K(Response);
    K --> A;
```

## 🧪 3. Estrategia de Testing (Gradual)

### Métricas por Fase
| Fase | Unit Coverage | Integration | Herramientas |
|------|---------------|-------------|--------------|
| **3A (Actual)** | 60% | 40% | pytest, respx |
| **3B (Q1)** | 75% | 60% | + snapshot testing |
| **3C (Q2)** | 85% | 75% | + contract testing |
| **Producción** | 90% | 85% | + mutation testing |

### Testing Actual
- ✅ Unit tests para core modules
- ✅ Integration tests para webhooks
- ✅ Snapshot tests para prompts
- 🚧 E2E tests para flujo completo

## 🗺️ 4. Roadmap Ejecutivo

### ✅ FASE 3A: MasterRouter Básico (COMPLETADA - 4 sem)
<!-- LLM-Hint: Phase 3A completed successfully. All milestones achieved. -->
**Objetivo:** Enrutamiento funcional sin LLM
**Estado:** ✅ COMPLETADA (5/5 hitos)
- ✅ Registry pattern implementado
- ✅ Enrutamiento por event_type
- ✅ Tests de integración
- ✅ Documentación de especialistas
- ✅ Cleanup de TODOs en código

**DoD Alcanzado:** Webhook → MasterRouter → TranscriptionAgent (100% funcional)

### ✅ FASE 3B: Sistema Conversacional + Memoria (COMPLETADA)
**Objetivo:** Sistema conversacional completo con memoria persistente  
**Estado:** ✅ COMPLETADA (4/4 hitos + refactorización ADR-0006)

**Logros Clave:**
- ✅ **UX Conversacional:** Audio/Texto → ChatAgent → Respuesta inteligente natural
- ✅ **Arquitectura Clean:** MasterOrchestrator Strategy Pattern (7 componentes)
- ✅ **Memoria Persistente:** Redis SessionManager con TTL 1h + cleanup automático
- ✅ **Observabilidad:** LangSmith integration completa (tracing + cost tracking)
- ✅ **Testing:** 85% coverage + integration tests + E2E flow validation

**DoD ALCANZADO:** "Usuario envía audio/texto → recibe respuesta inteligente y natural → puede referenciar conversación anterior + arquitectura limpia escalable"

### 🔮 FASE 3C: Vector DB Multi-Tenant + Características Avanzadas (10 sem) - **50% COMPLETADO**

**Objetivo:** Base vectorial multi-tenant + agentes modulares + características avanzadas

**✅ COMPLETADO (Foundation + Core Restoration):**
- ✅ ChromaDB multi-tenant para aislamiento de datos por usuario (Task #1)
- ✅ BaseModularAgent interface estable para composición (Task #2)
- ✅ VectorMemoryManager persistente por usuario (Task #3)  
- ✅ FileHandlerAgent con validación segura y parsing (Task #5)
- ✅ Sistema de roles USER/ADMIN/SUPER_ADMIN (Task #13)
- ✅ **Procesamiento de Archivos Multimodales** - ChatAgent → MasterOrchestrator → FileHandlerAgent (Task #7)
- ✅ **Herramientas Multimodales** - src/tools/multimodal_processor.py con registry pattern
- ✅ **CRITICAL MILESTONE:** Restauración COMPLETA ChatAgent ADR-0009 (Task #19)
- ✅ **Arquitectura Híbrida:** Performance optimizations + Funcionalidad completa
- ✅ **Performance Fix:** Function calling 36s → <2s routing
- ✅ **Delegación Inteligente:** ChatAgent 143→628 líneas - 100% funcional

**🎯 PRÓXIMO SPRINT (Observabilidad + Performance):**
- 📋 **PRIORITY:** Sistema Observabilidad LLM completo (Task #20)
- 📋 **PRIORITY:** Performance Profiling y Optimización (Task #21)
- 📋 Data Migration Script para arquitectura nueva (Task #22)

**🔄 PENDIENTE (Características Avanzadas - ADR-0008):**
- 📋 GlobalCollectionManager para collections compartidas (Task #14)
- 📋 SmartContentAnalyzer para filtrado inteligente (Task #15)
- 📋 HybridMemoryManager con estrategias local/cloud (Task #16)
- 📋 CrossTenantAccess para permisos entre usuarios (Task #17)

**🔄 PENDIENTE (Testing y Optimización):**
- 📋 E2E Testing & Validation completa (Task #11)
- 📋 Collections Granulares Decision Point (Task #12)
- ❌ ~~NLPParserAgent con intent recognition (Task #6)~~ - Cancelada: ChatAgent maneja NLP

**DoD ACTUAL:** "Usuario interactúa con ChatAgent completamente funcional → Delegación inteligente + traducción respuestas → Performance <2s routing + memoria persistente → Observabilidad completa LLM calls"

**DoD FINAL:** "Usuario interactúa con sistema multi-tenant avanzado → Collections globales + roles + análisis semántico → Memoria híbrida optimizada → Agentes modulares componibles dinámicamente"

### 🌟 FASE 4: Federación Completa (Q2)
- Múltiples especialistas con LangSmith observability
- Enrutamiento inteligente por LLM con métricas de costos
- Memoria a largo plazo distribuida en Redis
- Optimización de costos basada en datos LangSmith

## 🚀 5. Guía de Desarrollo

### Comandos Esenciales
```bash
# Desarrollo diario
make dev          # Docker + hot-reload
make verify       # CI completa (lint + test + security)
make format       # Auto-fix styling

# Estado del proyecto
curl localhost:8000/system/status  # Métricas en vivo
curl localhost:8000/metrics        # Prometheus
```

### Flujo Git/GitHub Completo

#### **Branching Strategy**
```
main         ← Releases estables (Production)
  ↑
develop      ← Integration branch (Pre-production)
  ↑
feature/*    ← Feature branches (Development)
```

#### **Workflow Detallado por Tipo de Trabajo**

##### **Para Fases Completas (ej. Fase 3A → 3B):**
```bash
# 1. Trabajar en feature branch
git checkout -b feature/nombre-descriptivo
# ... desarrollo ...
make verify && git commit

# 2. Mergear a develop
git checkout develop
git merge feature/nombre-descriptivo

# 3. PR develop → main (GitHub UI)
# - Usar notificación "develop had recent pushes"
# - Título: "feat: Complete Phase X - Description"
# - Merge via GitHub interface

# 4. Limpieza post-merge
git branch -d feature/nombre-descriptivo  # Local
# Eliminar también en GitHub UI
git remote prune origin  # Limpiar referencias
```

##### **Para Features Menores:**
```bash
# 1. Feature branch desde develop
git checkout develop && git pull origin develop
git checkout -b feature/small-feature

# 2. Desarrollo
make verify && git commit

# 3. PR directo feature → develop
git push origin feature/small-feature
# PR via GitHub UI → develop
```

##### **Manejo de Conflictos/Desfases:**
```bash
# Si remote tiene cambios
git fetch origin
git log develop..origin/develop  # Ver diferencias

# Opción A: Pull + merge
git pull origin develop

# Opción B: Force push (solo si estás seguro)
git push --force-with-lease origin develop
```

#### **Pull Request Guidelines**

##### **Títulos Estándar:**
```
feat(scope): Complete Phase X - Description
fix(scope): Corrige issue específico
docs(scope): Actualiza documentación
chore(scope): Limpieza o mantenimiento
```

##### **Descripción Template:**
```markdown
## 🎯 Objetivo
[Qué se logra con este PR]

## ✅ Cambios Principales
- [Lista de cambios importantes]
- [Funcionalidades nuevas]

## 🧪 Testing
- [Cómo se validó]
- [Quality gates que pasan]

## 📋 DoD Alcanzado
[Definition of Done específico]
```

#### **Limpieza Post-Merge (Mandatoria)**
```bash
# Después de cada merge exitoso
git branch -d feature/branch-name     # Eliminar local
# GitHub UI: Delete branch button     # Eliminar remoto
git remote prune origin              # Limpiar referencias
```

### Flujo de Desarrollo por Tipo

#### Para Cambios Mayores (APIs, Arquitectura)
1. **🚨 REVISAR CONTEXTO:** Read, LS, Grep, Glob para entender qué existe
2. **Planificar:** Crear/actualizar ADR relevante
3. **Branch:** `feature/major-change` desde develop
4. **Documentar:** Actualizar PROJECT_OVERVIEW.md si cambia roadmap
5. **Implementar:** Código + tests mínimos
6. **Validar:** `make verify` + PR review
7. **Merge:** develop → main para milestones

#### Para Cambios Menores (Features, Bugs)
1. **🚨 REVISAR CONTEXTO:** Read, LS, Grep para entender código existente
2. **Branch:** `feature/small-feature` desde develop
3. **Implementar:** Directo a código + tests
4. **Validar:** `make verify`
5. **PR:** feature → develop
6. **Limpieza:** Delete branch

#### Protocolo de Emergencia (Bugs Críticos)
1. **Hotfix:** Branch directo desde main
2. **Fix mínimo:** Solo lo necesario para restaurar servicio
3. **PR:** hotfix → main Y develop
4. **Post-mortem:** ADR documentando causa y prevención

### Gates de Calidad por Fase
```yaml
Fase_3A: ["make verify", "manual E2E test"]
Fase_3B: ["make verify", "redis integration test", "load test"]
Fase_3C: ["make verify", "E2E automation", "performance test"]
Producción: ["full CI/CD", "security scan", "chaos engineering"]
```

## 📊 6. Métricas y Migración

### Umbrales de Migración (Cuantitativos)
```yaml
Trigger_Distribuido:
  CPU_Sustained: ">80% por 5min"
  Memory_Sustained: ">85% por 3min"
  Latency_P95: ">5s transcripción"
  Error_Rate: ">2% en 24h"
  Concurrent_Users: ">100 simultáneos"

Estado_Actual:
  CPU: "~15% promedio"
  Memory: "~40% promedio"
  Latency_P95: "~1.2s transcripción"
  Error_Rate: "<0.1%"
  Users: "~5 concurrentes"
```

### Dashboard en Vivo
- **Estado:** `/system/status`
- **Métricas:** `/metrics` (Prometheus)
- **Logs:** `docker logs aegen-app`

---

## 🔧 7. Herramientas de Contexto

### Comandos de Estado del Proyecto
```bash
# Ver contexto completo
make status           # Estado git + testing + métricas

# Sincronizar documentación
make sync-docs        # Actualiza estado real en PROJECT_OVERVIEW.md

# Diagnóstico completo
make doctor          # Verifica consistencia docs vs código
```

### Integración con Desarrollo
- **VS Code:** `.vscode/settings.json` con configuración del proyecto
- **Git Hooks:** Pre-commit automático con formato y tests básicos
- **CI/CD:** GitHub Actions con gates graduales por fase

---

## 📚 8. Referencias Rápidas

### Documentos Normativos (Por Orden de Precedencia)
1. **Este documento** - Visión y roadmap
2. **`rules.md`** - Estándares técnicos obligatorios
3. **`adr/`** - Decisiones arquitectónicas (ADR-0007, ADR-0008 active)
4. **`.taskmaster/tasks/tasks.json`** - Task Master definiciones y progreso
5. **Código + tests** - Implementación actual

### Enlaces Útiles (Desarrollo Local)
- **API Docs:** http://localhost:8000/docs
- **Metrics:** http://localhost:8000/metrics
- **Status:** http://localhost:8000/system/status
- **Logs:** `docker logs -f aegen-app`

### Contactos y Escalación
- **Tech Lead:** `@jhomc` (Arquitectura, decisiones técnicas)
- **Documentación:** `PROJECT_OVERVIEW.md` + `rules.md`
- **Emergencias:** `make doctor` + revisión de logs

---

## 🎯 Próximos 30 Días

### ✅ Semana 1-2: Fase 3A Completada
- ✅ Tests de integración para MasterRouter
- ✅ Documentación de especialistas
- ✅ Cleanup de TODOs en código
- ✅ Performance baseline establecido

### ✅ Semana 3-4: Fase 3C Foundation COMPLETADA (ADR-0007)
- ✅ **COMPLETADO:** ChromaManager per-user collections + metadata filtering (Task #1)
- ✅ **COMPLETADO:** BaseModularAgent interface estable (Task #2) 
- ✅ **COMPLETADO:** VectorMemoryManager básico per-user (Task #3)
- ✅ **COMPLETADO:** FileHandlerAgent con validación + parsing + security (Task #5)
- ✅ **COMPLETADO:** Sistema de roles y permisos (Task #13)

### 🎯 Semana 5-6: Observabilidad y Performance Optimization
- [ ] **PRIORITY:** Sistema Observabilidad LLM completo (Task #20)
  - LLMCallTracker con métricas tiempo real
  - Middleware trazabilidad correlation_id  
  - Dashboard Grafana/Prometheus
  - Sistema alertas performance degradation
- [ ] **PRIORITY:** Performance Profiling end-to-end (Task #21)
  - Profile flujo Telegram → respuesta
  - Optimización caching routing analyzer
  - Connection pooling ChromaDB/Redis
- [ ] Data Migration Script collections existentes (Task #22)

### 🚀 Semana 7-8: Fase 3C Completion
- [ ] Sequential execution workflows (Task #7)
- [ ] HybridMemoryManager con estrategias local/cloud (Task #16)
- [ ] CrossTenantAccess para permisos entre usuarios (Task #17)
- [ ] Performance testing collections per-user (Task #8)
- [ ] SimpleComposer configuration-driven (Task #9)

### 📊 Semana 9-10: Fase 3C Final Integration  
- [ ] Hybrid memory Redis + ChromaDB integration (Task #10)
- [ ] E2E Testing & Validation completa (Task #11)
- [ ] **Decision Point**: Collections granulares needed based on performance data (Task #12)?

### Hitos Semanales
- **Viernes:** Demo del progreso semanal
- **Lunes:** Revisión de métricas y ajuste de plan
- **Miércoles:** Checkpoint técnico y deuda técnica

---

**🚀 Este documento es la fuente de verdad del proyecto. Se actualiza automáticamente con el estado real y evoluciona con nuestras decisiones. Para dudas específicas, consulta las referencias por precedencia o ejecuta `make doctor` para diagnóstico completo.**
