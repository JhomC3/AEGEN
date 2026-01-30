# Changelog

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.2.1] - 2026-01-30
### Added
- **Routing Precision V2**: Mejora drástica en la continuidad de hilos conversacionales.
  - Contexto de enrutamiento enriquecido con los últimos 5 mensajes (diálogo real).
  - Lógica de **Stickiness** (Afinidad): Inercia para mantener al especialista anterior si el tema es consistente.
  - Reglas de continuidad explícitas en el prompt del router.
- **Localization System**: Adaptación dinámica de MAGI al usuario.
  - Extracción automática de `language_code` desde webhooks.
  - Detección y persistencia de jerga regional (Argentino, Español, Mexicano).
  - Conciencia de zona horaria basada en el indicativo telefónico.
- **RAG Resilience**: Robustez en la gestión de archivos y conocimiento.
  - Implementación de **Exponential Backoff** para la activación de archivos en Google File API.
  - Filtro de búsqueda global mejorado para incluir bases de conocimiento (`CORE`, `GLOBAL`, `KNOWLEDGE`).
- **Robust JSON Extraction**: Nuevo extractor basado en regex que previene fallos por decoraciones Markdown del LLM en procesos de consolidación.

### Fixed
- Corregido error de pérdida de contexto en ejercicios de TCC.
- Eliminado error `JSONDecodeError` durante la consolidación de perfiles.
- Reducción de fallos de subida de archivos pesados a la Google File API.

## [v0.2.0] - 2026-01-29
  - `SystemPromptBuilder` modular para composición de prompts en 4 capas (Base, Adaptación, Skill, Runtime).
  - `PersonalityManager` para gestión de archivos Markdown de identidad (`SOUL.md`, `IDENTITY.md`).
  - `PersonalityEvolutionService` integrado en el ciclo de consolidación de memoria para aprendizaje continuo.
  - Overlays de personalidad por especialista (ej: "Amor Duro" para TCC).
  - Activación híbrida de especialistas: Detección automática + Comandos explícitos (`/tcc`, `/chat`).
- **Diskless Memory Architecture**: Migración completa a Redis + Google Cloud para una infraestructura stateless y escalable.
  - `RedisMessageBuffer` para gestión de mensajes pre-consolidación de alta velocidad.
  - `ConsolidationManager` para consolidación automática de historiales (N>=20 mensajes o 6h de inactividad).
  - Integración profunda con Google File Search API para almacenamiento y búsqueda semántica de historiales consolidados.
  - Soporte multi-usuario stateless en `ProfileManager` con caché en Redis y persistencia en la nube.
  - Nueva herramienta `query_user_history` para el especialista TCC.
- **Personalización Dinámica**: Respuestas adaptativas que utilizan el nombre del usuario y refuerzan la memoria conversacional activa.

### Changed
- `LongTermMemoryManager` refactorizado para eliminar dependencias del sistema de archivos local.
- `ChatAgent` y `CBT Specialist` ahora cargan perfiles de usuario dinámicamente mediante `chat_id`.
- Prompts terapéuticos actualizados para incentivar el uso de la memoria a largo plazo y la identidad del usuario.

### Removed
- Directorio `storage/` y toda dependencia de almacenamiento local persistente.
- Dependencia de `aiofiles` en módulos de memoria central.
- Variables de entorno y configuraciones relacionadas con paths locales (`STORAGE_DIR`).

## [v0.1.5] - 2025-12-19
### Fixed
- **Polling (Universal Fix):** Refactorizado `polling.py` para usar exclusivamente la librería estándar de Python (`urllib`, `json`). Eliminadas dependencias de `httpx` y `requests` que causaban fallos en entornos host sin entorno virtual activo (`systemctl`).

## [v0.1.4] - 2025-12-19
### Fixed
- **Polling:** Refactorizado `src/tools/polling.py` para usar `httpx` (asíncrono) en lugar de `requests`, alineando dependencias y resolviendo problemas de ejecución en entornos sin `requests` instalado.

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
-

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
