# AEGEN: Sistema de Agentes Evolutivo

> **Versión:** 10.0 (Edición "Contexto Dinámico y Pragmático")
> **Estado:** Activo y Evolutivo
> **Branch Actual:** `feature/conversational-flow-3b`
> **Última Actualización:** 2025-08-19

<!-- LLM-Hint: This document follows a strict hierarchy. In case of conflict, PROJECT_OVERVIEW.md (this file) has the highest authority. The current project phase is defined in the "Estado Real" YAML block below. Use the DoD (Definition of Done) for each phase to understand completion criteria. All sections marked with 🎯 are current focus areas. -->

## 🎯 Contexto Actual del Proyecto

### Estado Real (Semi-Automático)
<!-- LLM-Hint: This block is semi-automated. Git status and timestamp are updated by 'make sync-docs'. Phase progress and milestones must be updated manually upon completion. -->
```yaml
Fase_Actual: "PREPARANDO FASE 3C - Vector Database + Multi-Agent"
Progreso_Fase_3A: "5/5 hitos completados (✅ COMPLETADA)"
Progreso_Fase_3B: "4/4 hitos completados + refactorización crítica (✅ COMPLETADA)"
Progreso_Fase_3C: "0/8 hitos - Iniciando ChromaDB POC"
Próximo_Hito: "ChromaDB setup + user namespace privacy validation"
Funcionalidades_Activas:
  - ✅ Transcripción E2E via Telegram (faster-whisper optimizado)
  - ✅ MasterOrchestrator Strategy Pattern (7 componentes clean)
  - ✅ Schemas CanonicalEventV1/GraphStateV2 + contratos inter-agente
  - ✅ Sistema de testing (85% cobertura + integration tests)
  - ✅ LangSmith Integration (tracing completo + cost tracking)
  - ✅ Redis Session Memory (TTL 1h, persistencia robusta)
  - ✅ Memoria conversacional bidireccional (audio + texto)
  - ✅ ChatAgent como punto único entrada + delegación inteligente
  - ✅ Chaining transcription → planner → respuesta final
  - ✅ Calidad transcripción optimizada (ES, float32, VAD)
  - ✅ PR Phase 3B merged to develop successfully
Branch_Trabajo: "feature/phase3c-vector-multiagent"
Cambios_Pendientes: ["ChromaDB integration", "Privacy-first architecture", "Multiple specialist agents"]
Última_Sincronización: "2025-08-22 04:00"
```

### ¿Dónde Estamos Hoy?
- **✅ Completado:** Fase 3A - MasterRouter básico funcional
- **✅ Completado:** Fase 3B - Sistema conversacional completo con memoria persistente
- **✅ Completado:** Refactorización arquitectónica crítica (ADR-0006)
- **✅ Completado:** Pull Request Phase 3B merged successfully to develop
- **🎯 Iniciando:** Fase 3C - ChromaDB Vector Database + Multi-Agent Specialists
- **📊 Logrado:** LangSmith observabilidad LLM operacional
- **💾 Logrado:** Redis memoria conversacional robusta
- **🎉 Meta Alcanzada:** Sistema conversacional completo funcional con arquitectura limpia

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
│   │   ├── orchestrator.py  # ✅ MasterRouter básico
│   │   └── specialists/
│   │       ├── transcription_agent.py  # ✅ Funcional
│   │       └── chat_agent.py          # 🚧 En desarrollo
│   │
│   └── core/
│       ├── schemas.py       # ✅ CanonicalEventV1, GraphStateV1
│       ├── registry.py      # ✅ Autodescubrimiento
│       └── interfaces/      # ✅ Contratos TypeScript-style
│
├── 🛠️ Herramientas
│   ├── speech_processing.py    # ✅ Whisper integrado
│   ├── telegram_interface.py  # ✅ Bot API
│   └── document_processing.py # 🚧 Para InventoryAgent
│
└── 📊 Observabilidad
    ├── logging_config.py   # ✅ Structured JSON
    ├── middleware.py       # ✅ Correlation IDs
    └── /metrics           # ✅ Prometheus endpoint
```

### Flujo de Datos Actual
```mermaid
Telegram → Webhook → CanonicalEvent → MasterRouter → Specialist → Response
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

### 🔄 FASE 3B: Flujo Conversacional + Memoria (COMPLETADA + REFACTORING)
**Objetivo:** Sistema conversacional completo con memoria persistente

#### **Hitos Críticos Completados:**
1. **✅ Fix UX Crítico:** Audio → Transcript → ChatBot → Respuesta inteligente
   - ✅ Eliminar retorno directo de transcript al usuario
   - ✅ Enrutar transcript al ChatAgent para generar respuesta
   - ✅ Respuesta contextual basada en el audio transcrito
   - ✅ Migración a faster-whisper para Python 3.13

2. **✅ LangSmith Integration:** Observabilidad LLM nativa
   - ✅ Configuración LangSmith desde inicio (LANGCHAIN_TRACING_V2=true)
   - ✅ Tracing de prompts y respuestas
   - ✅ Proyecto AEGEN-Phase3B configurado
   - ✅ Debug de chains LLM

3. **✅ Memoria de Sesión Redis:** Estado conversacional persistente
   - ✅ Redis como store de sesiones por chat_id
   - ✅ GraphStateV2 serializable con historial conversacional
   - ✅ TTL automático y cleanup de sesiones (1 hora)
   - ✅ SessionManager con persistencia completa
   - ✅ Tests de persistencia conversacional

4. **✅ Testing Conversacional:** E2E con memoria
   - ✅ Tests de flujo completo: Audio → Respuesta → Memoria
   - ✅ Validación de persistencia entre mensajes
   - ✅ Tests de TTL y cleanup
   - ✅ Integration tests en tests/integration/

#### **✅ REFACTORIZACIÓN ARQUITECTÓNICA COMPLETADA (ADR-0006):**

**PROBLEMA RESUELTO:** Experiencia de usuario conversacional restaurada
- **✅ Eliminado:** Respuestas técnicas directas del PlannerAgent
- **✅ Implementado:** ChatAgent como único punto de entrada para texto
- **✅ Funcional:** Delegación inteligente con traducción a lenguaje natural

**Arquitectura Implementada - Strategy Pattern + Delegación:**
```
Usuario → ChatAgent (ÚNICO) → [análisis intención] → [respuesta directa | delegación]
                                                     ↓
        MasterOrchestrator ← [si delegación] ← Function Calling Router
                ↓
        Specialist Selection (event/function/chaining)
                ↓
        PlannerAgent → TranscriptionAgent → [otros especialistas]
                ↓
        Resultado + Chaining Logic
                ↓
        ChatAgent ← [Traduce respuesta técnica a conversacional]
                ↓
        Usuario ← Respuesta siempre natural + memoria persistente
```

**Cambios Completados:**
- [✅] **MasterOrchestrator Strategy Pattern:** 7 componentes separados clean
- [✅] **ChatAgent como único entry point:** Solo maneja event_type="text"
- [✅] **PlannerAgent capabilities:** Solo "planning", "coordination", "internal_planning_request"
- [✅] **Lazy initialization:** Thread-safe singleton con double-check locking
- [✅] **Chaining fix:** transcription_agent → planner_agent routing restaurado
- [✅] **Memoria conversacional:** Bidireccional para audio y texto
- [✅] **Calidad transcripción:** FasterWhisper optimizado (ES, float32, VAD)
- [✅] **Contratos inter-agente:** InternalDelegationRequest/Response schemas

**DoD ALCANZADO:** "Usuario envía audio/texto → recibe respuesta inteligente y natural → puede referenciar conversación anterior + arquitectura limpia escalable"

### 🔮 FASE 3C: ChromaDB Vector Database + Multi-Agent Specialists (8 sem)
**Objetivo:** Arquitectura privacy-first con vector database y múltiples especialistas
- ChromaDB integration con user namespacing para privacy
- FitnessAgent para análisis de datos de ejercicio y nutrición
- InventoryAgent para manipulación de archivos Excel vía conversación
- Privacy-first data management con separación user vs shared knowledge
- Vector search capabilities para knowledge retrieval
- Estado de archivo persistente en sesión Redis

**DoD:** "Usuario puede subir Excel fitness data → conversación inteligente para análisis → FitnessAgent procesa datos → respuestas basadas en vector knowledge + privacy garantizada"

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
3. **`adr/`** - Decisiones arquitectónicas
4. **Código + tests** - Implementación actual

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

### 🚧 Semana 3-4: Iniciar Fase 3B
- [ ] **CRÍTICO:** Fix UX - Audio → ChatBot → Respuesta inteligente
- [ ] LangSmith setup y configuración inicial
- [ ] Diseño de schema de sesión en Redis
- [ ] POC de persistencia de GraphStateV2
- [ ] Herramientas de debug para sesiones
- [ ] Tests de TTL y cleanup

### 🔜 Semana 5-6: Consolidar Fase 3B
- [ ] E2E testing con memoria conversacional
- [ ] Métricas LangSmith para costos por conversación
- [ ] Optimización de performance con Redis
- [ ] Documentación de arquitectura conversacional

### Hitos Semanales
- **Viernes:** Demo del progreso semanal
- **Lunes:** Revisión de métricas y ajuste de plan
- **Miércoles:** Checkpoint técnico y deuda técnica

---

**🚀 Este documento es la fuente de verdad del proyecto. Se actualiza automáticamente con el estado real y evoluciona con nuestras decisiones. Para dudas específicas, consulta las referencias por precedencia o ejecuta `make doctor` para diagnóstico completo.**
