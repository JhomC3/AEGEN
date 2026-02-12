# Registro de Cambios (Changelog)

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [No publicado]

## [v0.7.2] - 2026-02-11
### Añadido
- **Containerización del Polling de Telegram**: Integración del servicio de polling (`src/tools/polling.py`) directamente en `docker-compose.yml`.
  - Mayor resiliencia mediante reinicio automático (`unless-stopped`).
  - Desacoplamiento total del Host (GCE) eliminando la dependencia de `systemd`.
  - Mejora en la comunicación interna mediante la red de Docker (`http://app:8000`).
- **Robustez del Servicio de Polling**: Validación de `TELEGRAM_BOT_TOKEN` y manejo de errores mejorado para entornos de contenedor.

### Cambiado
- **Documentación de Despliegue**: Simplificación del manual de despliegue eliminando pasos de configuración manual del host.
- **Makefile**: Actualización de comandos `build` y `logs` para soportar la nueva arquitectura multi-servicio.

## [v0.7.1] - 2026-02-11
### Refactorización
- **Saneamiento Estructural Completo**: Eliminación de violaciones SRP y límites de LOC en todo el codebase.
  - **Webhooks**: Desacoplamiento en `adapters/telegram_adapter`, `services/debounce_manager`, `services/event_processor`.
  - **Routing**: Modularización en `graph_routing`, `pattern_extractor`, `intent_validator`.
  - **Memoria**: Delegación a `memory_summarizer`, `incremental_extractor`, `sqlite_store` (repositorios).
  - **Core**: Limpieza de `profile_manager`, `session_manager`, `logging_config`.
  - **Tools**: Separación de herramientas de Telegram.
- **Calidad**: Endurecimiento de tests con gate de cobertura al 50%. Script de arquitectura inteligente.

## [v0.6.0] - 2026-02-11
### Añadido
- **Arquitectura de Datos con Procedencia (Provenance)**: Implementación de trazabilidad completa en la memoria persistente.
  - Nuevas columnas en `memories`: `source_type` (explicit/observed/inferred), `confidence`, `sensitivity`, `evidence`.
  - Soporte para **Borrado Suave (Soft Delete)** (`is_active`) en todas las capas (SQL, Hybrid Search, VMM).
  - Motor de migraciones asíncronas e idempotentes en `src/memory/migration.py`.
- **Perfil Evolutivo Enriquecido (Pydantic)**: Migración del perfil de usuario a modelos Pydantic validados.
  - Nuevas dimensiones: `support_preferences`, `coping_mechanisms`, `clinical_safety`.
  - Migración automática y transparente de perfiles antiguos al cargar.
- **Seguridad Clínica y Guardrails (Protecciones)**: Blindaje ético y profesional del especialista CBT.
  - Detector de vulnerabilidad con derivación a recursos de emergencia integrados en el perfil.
  - Restricciones explícitas de "No Diagnóstico" y "No Prescripción" en el motor de prompts.
  - Nuevo sistema de **Transparencia RAG**: Registros (Logs) detallados de qué fragmentos de conocimiento se inyectan en cada respuesta.
- **Controles de Privacidad del Usuario**: Interfaz de comandos para el control total de datos.
  - `/privacidad`: Estadísticas de memoria por tipo y sensibilidad.
  - `/olvidar [tema]`: Borrado semántico de memorias relacionadas.
  - `/efimero`: Modo de sesión sin persistencia.
  - `/disclaimer`: Advertencia legal y recursos de ayuda.
- **Herramientas de Mantenimiento**:
  - `scripts/migrate_provenance.py`: Saneamiento de espacios de nombres (namespaces) y contaminación de datos.
  - `scripts/sync_knowledge.py`: Punto de entrada robusto para indexación de PDFs.
  - `scripts/archive_legacy.py`: Limpieza física de archivos personales antiguos.

### Cambiado
- **Estabilidad del Sistema**: Mejorada la resiliencia del arranque mediante ejecución asíncrona de la sincronización de conocimiento.
- **Optimización de Docker**: Imagen reconstruida para incluir herramientas de mantenimiento y soporte de módulos Python en la carpeta `scripts/`.
- **Confiabilidad Mejorada**: Implementado bloqueo de concurrencia (`asyncio.Lock`) en SQLiteStore para evitar "base de datos bloqueada" (database locked).

## [v0.3.0] - 2026-02-07
### Añadido
- **Arquitectura de Memoria Local-First Híbrida (Fase F)**: Inicio de la migración hacia una persistencia local optimizada.
  - Diseño de esquema SQLite con soporte para búsqueda vectorial (`sqlite-vec`) y texto completo (`FTS5`).
  - Plan de implementación de 7 fases para eliminar la dependencia crítica de la Google File API.
  - Nuevo flujo (pipeline) de ingestión con fragmentación (chunking) recursiva (400/80 tokens) y deduplicación por resumen (hash) SHA-256.
  - Algoritmo de clasificación (ranking) híbrido RRF (Reciprocal Rank Fusion) para combinar resultados semánticos y léxicos.
- **Estructura de Documentación Mejorada**: Reorganización de la documentación técnica.
  - Carpeta `docs/archive/memory_evolution_v0.3/` para el seguimiento del cambio arquitectónico.
  - Carpeta `docs/research/` para investigaciones técnicas y referencias (ej: OpenClaw).

### Cambiado
- **Actualización de Documentación**: Actualizados `README.md`, `PROJECT_OVERVIEW.md` para reflejar la nueva dirección arquitectónica.
- Actualizada la versión del proyecto a 0.3.0 (Memory Evolution).

## [v0.2.2] - 2026-02-04
### Añadido
- **Sistema de Identidad Estructural**: Implementación del flujo completo de identidad del usuario.
  - Captura de `first_name` desde webhooks de Telegram.
  - Método `seed_identity_from_platform` para inicialización no destructiva del perfil.
  - Extracción proactiva del nombre del usuario desde la conversación mediante `FactExtractor`.
  - Sincronización automática de hechos de identidad (`Knowledge Base`) hacia el perfil persistente.
- **Robustez de Prompts**: Implementado escapado de seguridad de llaves `{}` en `SystemPromptBuilder` para prevenir caídas (crashes) de LangChain por variables de plantilla no resueltas.
- **Sanitización de Nombres de Archivo RAG**: Reescrita la lógica de limpieza de nombres en `GoogleFileSearchTool` con truncado inteligente (64 caracteres) para cumplir con las restricciones de la API de Google.

### Cambiado
- Revertido código fijo (hardcode) de identidad de administrador en `prompt_builder.py` en favor del sistema estructural.
- Mejorado el tipado de eventos canónicos para incluir `first_name`.

### Corregido
- Corregido error `INVALID_PROMPT_INPUT` al inyectar JSONs o diccionarios en los system prompts.
- Solucionados errores de longitud de nombre en la Google File API para archivos con rutas profundas.

## [v0.2.1] - 2026-01-30
### Añadido
- **Precisión de Enrutamiento (Routing) V2**: Mejora drástica en la continuidad de hilos conversacionales.
  - Contexto de enrutamiento enriquecido con los últimos 5 mensajes (diálogo real).
  - Lógica de **Afinidad (Stickiness)**: Inercia para mantener al especialista anterior si el tema es consistente.
  - Reglas de continuidad explícitas en el prompt del enrutador.
- **Sistema de Localización**: Adaptación dinámica de MAGI al usuario.
  - Extracción automática de `language_code` desde webhooks.
  - Detección y persistencia de jerga regional (Argentino, Español, Mexicano).
  - Conciencia de zona horaria basada en el indicativo telefónico.
- **Resiliencia RAG**: Robustez en la gestión de archivos y conocimiento.
  - Implementación de **Retroceso Exponencial (Exponential Backoff)** para la activación de archivos en Google File API.
  - Filtro de búsqueda global mejorado para incluir bases de conocimiento (`CORE`, `GLOBAL`, `KNOWLEDGE`).
- **Extracción de JSON Robusta**: Nuevo extractor basado en expresiones regulares (regex) que previene fallos por decoraciones Markdown del LLM en procesos de consolidación.

### Corregido
- Corregido error de pérdida de contexto en ejercicios de TCC.
- Eliminado error `JSONDecodeError` durante la consolidación de perfiles.
- Reducción de fallos de subida de archivos pesados a la Google File API.

## [v0.2.0] - 2026-01-29
### Añadido
- **Personalidad Adaptativa**:
  - `SystemPromptBuilder` modular para composición de prompts en 4 capas (Base, Adaptación, Skill, Runtime).
  - `PersonalityManager` para gestión de archivos Markdown de identidad (`SOUL.md`, `IDENTITY.md`).
  - `PersonalityEvolutionService` integrado en el ciclo de consolidación de memoria para aprendizaje continuo.
  - Capas (Overlays) de personalidad por especialista (ej: "Amor Duro" para TCC).
  - Activación híbrida de especialistas: Detección automática + Comandos explícitos (`/tcc`, `/chat`).
- **Arquitectura de Memoria Diskless (Sin Disco)**: Migración completa a Redis + Google Cloud para una infraestructura sin estado (stateless) y escalable.
  - `RedisMessageBuffer` para gestión de mensajes pre-consolidación de alta velocidad.
  - `ConsolidationManager` para consolidación automática de historiales (N>=20 mensajes o 6h de inactividad).
  - Integración profunda con Google File Search API para almacenamiento y búsqueda semántica de historiales consolidados.
  - Soporte multi-usuario sin estado en `ProfileManager` con caché en Redis y persistencia en la nube.
  - Nueva herramienta `query_user_history` para el especialista TCC.
- **Personalización Dinámica**: Respuestas adaptativas que utilizan el nombre del usuario y refuerzan la memoria conversacional activa.

### Cambiado
- `LongTermMemoryManager` refactorizado para eliminar dependencias del sistema de archivos local.
- `ChatAgent` y `CBT Specialist` ahora cargan perfiles de usuario dinámicamente mediante `chat_id`.
- Prompts terapéuticos actualizados para incentivar el uso de la memoria a largo plazo y la identidad del usuario.

### Eliminado
- Directorio `storage/` y toda dependencia de almacenamiento local persistente (en esta versión).
- Dependencia de `aiofiles` en módulos de memoria central.
- Variables de entorno y configuraciones relacionadas con rutas locales (`STORAGE_DIR`).

## [v0.1.5] - 2025-12-19
### Corregido
- **Sondeo (Polling) (Arreglo Universal):** Refactorizado `polling.py` para usar exclusivamente la librería estándar de Python (`urllib`, `json`). Eliminadas dependencias de `httpx` y `requests` que causaban fallos en entornos host sin entorno virtual activo (`systemctl`).

## [v0.1.4] - 2025-12-19
### Corregido
- **Sondeo (Polling):** Refactorizado `src/tools/polling.py` para usar `httpx` (asíncrono) en lugar de `requests`, alineando dependencias y resolviendo problemas de ejecución en entornos sin `requests` instalado.

## [v0.1.3] - 2025-12-19
### Añadido
- **Optimización de Consumo y Modelo**:
  - **Configuración:** Actualizado modelo por defecto a `gemini-flash-lite-latest`.
  - **Enrutamiento de Ruta Rápida (Fast Path Routing):** Implementado sistema de detección Regex para saludos (ahorro 50% de consumo).
  - **UX (Experiencia de Usuario):** Mensajes de error de cuota específicos.

## [v0.1.2] - 2025-12-19
### Corregido
- **Memoria:** Refactorizado `LongTermMemoryManager` para usar `aiofiles` para I/O no bloqueante.
- **Agentes:** Corregido argumento `original_event` faltante en la lógica de delegación de `ChatAgent`.
- **Motor (Engine):** Resueltas discrepancias de tipos de Mypy en la inicialización de `ChatGoogleGenerativeAI`.
- **Seguridad:** Añadidos tiempos de espera (timeouts) a las peticiones de red en `polling.py` y mejorado el manejo de excepciones.
- **Calidad:** Logrado el 100% de cumplimiento con Ruff, Mypy y Bandit.

### Añadido
- **Sistema de Agrupación de Mensajes - Intelligent Message Grouping (Tarea #23)**:
  - Solución crítica para mensajes fuera de orden en sistema asíncrono.
  - Sistema de eliminación de rebotes (debounce) inteligente: agrupa mensajes consecutivos en respuesta coherente.
  - Optimización significativa: reduce 40%+ llamadas LLM/DB (3 mensajes → 1 respuesta).
  - Almacenamiento intermedio basado en Redis con tiempo de espera configurable.
  - Respaldo (fallback) robusto a procesamiento individual en caso de errores.
  - ADR-0011 completo con análisis técnico y consenso AI favorable.
- **Implementación del Sistema de Observabilidad LLM (Tarea #20)**:
  - Seguimiento completo de llamadas LLM con métricas Prometheus.
  - IDs de correlación para trazabilidad de extremo a extremo.
  - Puntos de entrada (endpoints) de API para monitoreo: `/system/llm/status`, `/metrics/summary`, `/health`.
- Tests de validación reorganizados en estructura `tests/performance/` y `tests/integration/`.
- Implementación de la gobernanza ejecutable (v9.0 del `PROJECT_OVERVIEW.md`).
- Creación de los artefactos normativos: `RULES.MD`, `adr/`.
- Estructura de directorios para `adr`, `playbooks`, `prompts` y `tests` de evaluación.

## [v0.1.1] - 2025-12-19 (Hotfixes)
### Corregido
- **CRÍTICO:** Corrección de `DefaultCredentialsError` en arranque. Se inyecta explícitamente `GOOGLE_API_KEY` en `ChatGoogleGenerativeAI` para evitar respaldo (fallback) erróneo a Application Default Credentials (ADC).
- **CRÍTICO:** Solución a `AttributeError` en `LongTermMemoryManager`. Se forzó actualización de código para resolver desajuste de versiones en despliegues (método `_get_local_path` faltante).
- Estabilización de despliegue en GCP Free Tier.

## [1.0.0] - 2025-08-13
### Añadido
- Fase 1 completada: Agente de transcripción de extremo a extremo funcional.
