# Changelog

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implementación del Sistema de Observabilidad LLM (Task #20)
  - Tracking completo de llamadas LLM con métricas Prometheus
  - Correlation IDs para trazabilidad end-to-end
  - API endpoints para monitoreo: `/system/llm/status`, `/metrics/summary`, `/health`
  - Guía de usuario completa en `OBSERVABILIDAD_GUIA.md`
- Tests de validación reorganizados en estructura `tests/performance/` y `tests/integration/`
- Implementación de la gobernanza ejecutable (v9.0 del `PROJECT_OVERVIEW.md`)
- Creación de los artefactos normativos: `rules.md`, `adr/`
- Estructura de directorios para `adr`, `playbooks`, `prompts` y `tests` de evaluación

### Fixed
- Errores críticos de routing en production:
  - `NameError: ResourceExhausted is not defined` con imports fallback
  - `ValidationError: next_actions should be valid list` en RoutingDecision
  - `TypeError: ObservableLLM not compatible with Runnable` con nueva arquitectura
  - `TypeError: unsupported format string` en observability logging
- Sistema de routing completamente estabilizado y operativo
- Performance optimizada: respuestas en ~2.3s (target <3s cumplido)

## [1.0.0] - 2025-08-13

### Added
- Fase 1 completada: Agente de transcripción end-to-end funcional.
