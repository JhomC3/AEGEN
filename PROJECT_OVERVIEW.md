# AEGEN: Sistema de Agentes Evolutivo

> **Versión:** 10.0 (Edición "Contexto Dinámico y Pragmático")
> **Estado:** Activo y Evolutivo
> **Branch Actual:** `feature/telegram-transcription-workflow`
> **Última Actualización:** 2025-08-18

<!-- LLM-Hint: This document follows a strict hierarchy. In case of conflict, PROJECT_OVERVIEW.md (this file) has the highest authority. The current project phase is defined in the "Estado Real" YAML block below. Use the DoD (Definition of Done) for each phase to understand completion criteria. All sections marked with 🎯 are current focus areas. -->

## 🎯 Contexto Actual del Proyecto

### Estado Real (Semi-Automático)
<!-- LLM-Hint: This block is semi-automated. Git status and timestamp are updated by 'make sync-docs'. Phase progress and milestones must be updated manually upon completion. -->
```yaml
Fase_Actual: "FASE 3A - MasterRouter Básico"
Progreso_Fase_3: "5/5 hitos completados (Fase 3A ✅)"
Próximo_Hito: "Memoria de Sesión (Fase 3B)"
Funcionalidades_Activas:
  - ✅ Transcripción E2E via Telegram
  - ✅ MasterRouter con enrutamiento básico
  - ✅ Schemas CanonicalEventV1/GraphStateV1
  - 🚧 Sistema de testing (40% cobertura)
Branch_Trabajo: "feature/telegram-transcription-workflow"
Cambios_Pendientes: ['tests/integration/test_telegram_webhook.py', 'PROJECT_OVERVIEW.md', 'src/api/routers/webhooks.py', 'tests/conftest.py', 'src/tools/documents/process_documents.py']
Última_Sincronización: "2025-08-18 20:06"
```

### ¿Dónde Estamos Hoy?
- **Funciona:** Sistema completo de transcripción desde Telegram
- **En Desarrollo:** Enrutamiento dinámico y memoria de sesión
- **Siguiente:** InventoryAgent para manejo de archivos Excel
- **Meta 30 días:** Conversaciones multi-turno con contexto

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

### 🎯 FASE 3A: MasterRouter Básico (Actual - 4 sem)
<!-- LLM-Hint: Phase 3A progress is tracked by the completion of the checklist below. The sync-docs script automatically counts completed items. Each ✅ represents a completed milestone, 🚧 is in progress, ❌ is not started. -->
**Objetivo:** Enrutamiento funcional sin LLM
**Estado:** ✅ COMPLETADA (5/5 hitos)
- ✅ Registry pattern implementado
- ✅ Enrutamiento por event_type
- ✅ Tests de integración
- ✅ Documentación de especialistas
- ✅ Cleanup de TODOs en código

**DoD:** Webhook → MasterRouter → TranscriptionAgent (100% funcional)

### 🔜 FASE 3B: Memoria de Sesión (6 sem)
**Objetivo:** Estado conversacional persistente
- Redis como store de sesiones
- GraphStateV1 serializable
- TTL y cleanup automático
- Tests de persistencia

**DoD:** Usuario puede referenciar conversación anterior

### 🔮 FASE 3C: InventoryAgent (8 sem)
**Objetivo:** Primer especialista con estado
- Manipulación de archivos Excel
- Herramientas de spreadsheet
- Estado de archivo en sesión
- Flujo multi-turno E2E

**DoD:** "Sube Excel → modificalo por voz → descarga resultado"

### 🌟 FASE 4: Federación Completa (Q2)
- Múltiples especialistas
- Enrutamiento inteligente por LLM
- Memoria a largo plazo
- Optimización de costos

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

### Flujo de Desarrollo Simplificado

#### Para Cambios Mayores (APIs, Arquitectura)
1. **Planificar:** Crear/actualizar ADR relevante
2. **Documentar:** Actualizar este archivo si cambia roadmap
3. **Implementar:** Código + tests mínimos
4. **Validar:** `make verify` + PR review

#### Para Cambios Menores (Features, Bugs)
1. **Implementar:** Directo a código + tests
2. **Validar:** `make verify`
3. **Mergear:** PR + approval

#### Protocolo de Emergencia (Bugs Críticos)
1. **Hotfix:** Branch directo desde main
2. **Fix mínimo:** Solo lo necesario para restaurar servicio
3. **Post-mortem:** ADR documentando causa y prevención

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
2. **`PRD.md`** - Requisitos de producto y KPIs
3. **`rules.md`** - Estándares técnicos obligatorios
4. **`adr/`** - Decisiones arquitectónicas
5. **Código + tests** - Implementación actual

### Enlaces Útiles (Desarrollo Local)
- **API Docs:** http://localhost:8000/docs
- **Metrics:** http://localhost:8000/metrics
- **Status:** http://localhost:8000/system/status
- **Logs:** `docker logs -f aegen-app`

### Contactos y Escalación
- **Tech Lead:** `@jhomc` (Arquitectura, decisiones técnicas)
- **Product:** `PRD.md` (Requisitos, priorización)
- **Emergencias:** Canal `#aegen-alerts` + `make doctor`

---

## 🎯 Próximos 30 Días

### Semana 1-2: Completar Fase 3A
- [ ] Tests de integración para MasterRouter
- [ ] Documentación de especialistas
- [ ] Cleanup de TODOs en código
- [ ] Performance baseline

### Semana 3-4: Iniciar Fase 3B
- [ ] Diseño de schema de sesión en Redis
- [ ] POC de persistencia de GraphStateV1
- [ ] Herramientas de debug para sesiones
- [ ] Tests de TTL y cleanup

### Hitos Semanales
- **Viernes:** Demo del progreso semanal
- **Lunes:** Revisión de métricas y ajuste de plan
- **Miércoles:** Checkpoint técnico y deuda técnica

---

**🚀 Este documento es la fuente de verdad del proyecto. Se actualiza automáticamente con el estado real y evoluciona con nuestras decisiones. Para dudas específicas, consulta las referencias por precedencia o ejecuta `make doctor` para diagnóstico completo.**
