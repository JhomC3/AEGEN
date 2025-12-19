# Changelog

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.3] - 2025-12-19
### Optimización de Consumo y Modelo
- **Configuración:** Actualizado modelo por defecto a `gemini-flash-lite-latest`.
- **Fast Path Routing:** Implementado sistema de detección Regex para saludos (ahorro 50% de consumo).
- **UX:** Mensajes de error de cuota específicos.

## [0.1.2] - 2025-12-19
### Fixed
- **Memory:** Refactorized `LongTermMemoryManager` to use `aiofiles` for non-blocking I/O.
- **Agents:** Fixed missing `original_event` argument in `ChatAgent` delegation logic.
- **Engine:** Resolved Mypy type discrepancies in `ChatGoogleGenerativeAI` initialization.
- **Security:** Added timeouts to network requests in `polling.py` and improved exception handling.
- **Quality:** Achieved 100% compliance with Ruff, Mypy, and Bandit.

### Added
- **Message Bundling System - Intelligent Message Grouping (Task #23)**
  - Solución crítica para mensajes fuera de orden en sistema asíncrono
  - Sistema debounce inteligente: agrupa mensajes consecutivos en respuesta coherente
  - Optimización significativa: reduce 40%+ llamadas LLM/DB (3 mensajes → 1 respuesta)
  - Redis-based buffering con timeout configurable (1.5s MVP conservador)
  - Fallback robusto a procesamiento individual en caso de errores
  - ADR-0011 completo con análisis técnico y consensus AI favorable
  - Métricas de éxito definidas: UX improvement + cost optimization
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

### Fixed (Hotfixes v0.1.1 - 2025-12-19)
- **CRÍTICO:** Corrección de `DefaultCredentialsError` en arranque. Se inyecta explícitamente `GOOGLE_API_KEY` en `ChatGoogleGenerativeAI` para evitar fallback erróneo a Application Default Credentials (ADC).
- **CRÍTICO:** Solución a `AttributeError` en `LongTermMemoryManager`. Se forzó actualización de código para resolver mismatch de versiones en despliegues (método `_get_local_path` faltante).
- Estabilización de despliegue en GCP Free Tier.

## [1.0.0] - 2025-08-13

### Added
- Fase 1 completada: Agente de transcripción end-to-end funcional.
