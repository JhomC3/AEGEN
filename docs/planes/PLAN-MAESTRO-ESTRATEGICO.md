# PLAN: Estratégico Maestro de Implementación (AEGEN)

> **Instrucciones para Agentes:**
>
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** En Ejecución
- **Fecha:** 2026-02-12 (última auditoría: 2026-05-29)
- **Razón de Creación:** Planificación a largo plazo para la evolución del sistema AEGEN hacia la autonomía total.
- **Objetivo General:** Transformar AEGEN en un sistema de IA autónomo, profesional, con memoria persistente y capacidades de acción externa.
- **Versión actual:** v0.9.0 (CHANGELOG.md) — `pyproject.toml` sincronizado a `0.9.0`.

---

## Resumen Ejecutivo

Este plan maestro define la hoja de ruta técnica para AEGEN. Se divide en cuatro bloques fundamentales: Saneamiento (Bloque A), Expansión de Memoria (Bloque B), Capacidad de Acción (Bloque C) y Auto-mejora del Sistema (Bloque D). El sistema completó el saneamiento estructural en v0.9.0 (Graph-RAG, Two-Stage Retrieval, ingesta atómica). Los bloques A y C contienen bugs críticos activos que bloquean funcionalidad ya mergeada.

### Bugs críticos confirmados por auditoría (2026-05-29) — TODOS CORREGIDOS ✅

| ID    | Bug                                                                                                                                                                                | Archivos                                           | Impacto                                       | Estado |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- | ------ |
| BUG-1 | `analytical_intents` en `context_retriever.py` usaba strings inexistentes en `IntentType` — Graph-RAG nunca se activaba                                                            | `src/agents/orchestrator/context_retriever.py`     | ADR-0033 era código muerto                    | ✅ FIX |
| BUG-2 | `CASUAL_INTENTS` en `context_retriever.py` usaba strings inexistentes en `IntentType` — el skip de búsqueda semántica nunca operaba                                                | `src/agents/orchestrator/context_retriever.py`     | RAG se ejecutaba en saludos                   | ✅ FIX |
| BUG-3 | `"psicotrading"` faltaba en el `Literal` de `routing_tools.py` — el LLM nunca podía enrutar al especialista psicotrading                                                           | `src/agents/orchestrator/routing/routing_tools.py` | Especialista psicotrading inaccesible vía LLM | ✅ FIX |
| BUG-4 | `extract_model_info` en `metrics_processor.py` solo detectaba `ChatGoogleGenerativeAI` — Groq/OpenRouter producían `provider="unknown"`                                            | `src/core/observability/metrics_processor.py`      | Telemetría ciega para 80%+ de llamadas LLM    | ✅ FIX |
| BUG-5 | `pyproject.toml` declaraba versión `0.7.2` pero el proyecto estaba en `v0.9.0`                                                                                                     | `pyproject.toml`                                   | Versión incorrecta en metadata del paquete    | ✅ FIX |

---

## Bloque A: Saneamiento y Autonomía

### Objetivo

Limpieza total de deuda técnica y automatización de la gestión de conocimientos.

### Justificación

La base legacy de Google Cloud y la dispersión de datos impedían el escalado y la privacidad "local-first" deseada.

### Tareas y Estado

- [x] **A.1 Saneamiento de Raíz**: Unificación de almacenamiento en `/storage` y eliminación de scripts legacy. (Finalizado ✅ 2026-02-11)
- [x] **A.2 Vigilante de Conocimiento**: Sincronización automática de archivos en `storage/knowledge/`. (Finalizado ✅ 2026-02-13)
- [x] **A.3 Overhaul de Personalidad**: Implementación de arquitectura Soul Stack v2 y Espejo Natural. (Finalizado ✅ 2026-02-15)
- [ ] **A.4 Refactor del Sistema de Intents (Prioridad Máxima)**:
  - **Problema 1 — Graph-RAG muerto (BUG-1):** El `context_retriever.py` hardcodea 3 intents analíticos (`life_review`, `pattern_analysis`, `cross_domain_query`) que **no existen en `IntentType`**. El Graph-RAG (ADR-0033) nunca se activa en producción.
  - **Problema 2 — RAG en saludos (BUG-2):** `CASUAL_INTENTS` en `context_retriever.py` usa strings (`casual_greeting`, `farewell`, `acknowledgement`) que tampoco existen en `IntentType`. El skip semántico nunca opera. El RAG se ejecuta innecesariamente en cada saludo.
  - **Problema 3 — Psicotrading inaccesible (BUG-3):** `routing_tools.py` tiene un `Literal` con 10 intents pero falta `psicotrading` que sí existe en el enum. El LLM no puede enrutar al especialista psicotrading vía function calling.
  - **Solución integral:**
    1. Eliminar la dependencia de intents string para Graph-RAG. Reemplazar por detección data-driven: `SELECT 1 FROM memory_edges WHERE origen_id IN (...) LIMIT 1`. Si existen aristas, expandir el grafo; costo <5ms si no hay aristas.
    2. Reemplazar el `Literal` hardcodeado en `routing_tools.py` por `IntentType` como tipo del parámetro `intent`. LangChain extrae los valores del enum automáticamente. Esto elimina la raíz de BUG-3 y reduce las fuentes de verdad de 4 a 1.
    3. Alinear `CASUAL_INTENTS` con detección por regex sobre texto del mensaje (no depende del enum).
    4. Crear un test de integración que verifique que la anotación del router es `IntentType` y que ningún archivo hardcodea strings de intents.
  - **ADR requerido:** ADR-0034 (ver `adr/ADR-0034-graph-rag-data-driven.md`)
  - (Finalizado ✅ 2026-05-30)
- [x] **A.5 Migrar Facts Legacy a Atómicos en Producción (Prioridad Máxima)**:
  - **Problema:** 439 facts del usuario `6095416210` están en formato JSON blob (pre-ADR-0032). El RAG no puede encontrarlos semánticamente.
  - **Solución:** Ejecutar `make migrate-facts` en la VM de GCP para re-ingestar cada hecho como registro atómico individual con su propio embedding.
  - (Finalizado ✅ 2026-05-31 — 366 hechos atómicos individuales re-ingeridos)
- [x] **A.6 Re-ingestar PDFs Globales con SemanticChunker (Prioridad Máxima)**:
  - **Problema:** Los PDFs en `storage/knowledge/` (TCC, DSM-5) fueron ingeridos con el chunker recursivo plano (400 tok). No tienen estructura jerárquica (Nivel 3 → Nivel 4) ni purificación de ruido.
  - **Solución:** Re-procesar los PDFs usando `use_semantic_chunker=True` en el `IngestionPipeline`. Esto generará chunks padres (Nivel 3) e hijos (Nivel 4) vinculados por `parent_id`, con contenido purificado de ruido.
  - **Verificación:** Los chunks existentes se marcan `is_active=0`. Los nuevos chunks reemplazan a los viejos. El RAG debe encontrar fragmentos semánticamente coherentes en lugar de texto partido a la mitad.
  - (Finalizado ✅ 2026-05-31 — Sistema KnowledgeManager implementado, 57 chunks jerárquicos generados)
- [x] **A.7 Activar Respaldo en GCS (Prioridad Máxima)**:
  - **Problema:** `GCS_BACKUP_BUCKET = None`. El `CloudBackupManager` es funcional pero nunca se activó. Si la VM se destruye, se pierden todos los datos.
  - **Solución:**
    1. Crear bucket GCS (ej. `aegen-backups`) con retention policy de 30 días
    2. Configurar `GCS_BACKUP_BUCKET` y `GCS_CREDENTIALS_JSON` en el `.env` de la VM
    3. Verificar en logs que el backup se ejecuta tras cada consolidación
  - (Finalizado ✅ 2026-05-31 — Bucket `aegen-backups-jjhonn` creado con lifecycle de 30 días)
- [x] **A.8 Snapshots Periódicos del Disco de la VM (Prioridad Alta)**:
  - **Problema:** Sin respaldo cloud, el disco de la VM es el único almacén. Un fallo del disco o un delete accidental de la VM destruye todo.
  - **Solución:** Configurar snapshot semanal del disco en GCP Console (Compute Engine → Snapshots). Retención de 4 semanas.
  - (Finalizado ✅ 2026-05-31 — Programación automática asignada al disco)
- [ ] **A.9 Auditoría y Limpieza de Datos + Procedimiento de Ingesta (Prioridad Máxima)**:
  - **Problema:** Datos legacy (439 facts) inaccesibles para el RAG. Entorno local inconsistente con producción. Sin procedimiento documentado para ingesta de conocimiento.
  - **Solución:**
    1. Ejecutar `make migrate-facts` en GCP
    2. Eliminar archivos locales obsoletos (`storage/memory.db`, `storage/memory.sqlite`, `storage/backups/*.db`)
    3. Documentar procedimiento de ingesta en `docs/guias/manual-gestion-conocimiento.md`:
       - Conocimiento global: PDFs en `storage/knowledge/` → ingestión automática
       - Datos de usuario: Bulk Ingestor para WhatsApp, Claude, ChatGPT
       - Documentos personales: ingesta vía pipeline de documentos
    4. El pipeline debe soportar chunking semántico (Nivel 3→4) global y por usuario
    5. Verificar mensualmente la integridad de los datos en GCP
  - **Dependencia:** A.5 (migración de facts), B.1 (Bulk Ingestor)
  - (Pendiente ⏳)
- [ ] **A.10 Auditoría y Optimización de Modelos LLM (Prioridad Máxima)**:
  - **Problema:** Los logs muestran uso de Minimax vía OpenRouter para CBT (3s, 6479 tokens). La auditoría revela que Minimax es solo el fallback de `get_analytical_llm()`, pero se activó porque Groq no respondió a tiempo o falló. Adicionalmente, no se están usando las API keys gratuitas de Google AI Studio disponibles. El usuario dispone de múltiples cuentas que deberían rotarse para maximizar rate limits.
  - **Solución:**
    1. Investigar por qué Groq falla para `get_analytical_llm()` y `get_fast_llm()` en producción
    2. Evaluar migrar `REASONING_MODEL` a Gemini Flash para eliminar dependencia de OpenRouter
    3. Implementar `RoundRobinKeyProvider` (ADR-0035, sección 6) para rotar múltiples API keys de Google automáticamente, con cooldown de 60s ante rate limits
    4. Si se confirma Gemini como analytical LLM, actualizar `ADR-0027` (Inteligencia Asimétrica)
  - **ADR requerido:** ADR-0035 (sección 6)
  - (Finalizado ✅ 2026-05-30 — RoundRobinKeyProvider implementado)
- [ ] **A.11 Sincronizar versión en `pyproject.toml` (Prioridad Baja — BUG-5)**:
  - **Problema:** `pyproject.toml` declaraba `version = "0.7.2"` pero el proyecto estaba en `v0.9.0` según `CHANGELOG.md` y `AGENTS.md`.
  - **Solución:** Actualizado `version` en `pyproject.toml` a `"0.9.0"`.
  - (Finalizado ✅ 2026-05-30)
- [ ] **A.12 Desacoplamiento de Proveedores LLM (Prioridad Alta — A Discutir)**:
  - **Problema:** `src/core/engine.py` tiene los proveedores LLM hardcodeados en funciones específicas (Groq para analítico, OpenRouter como fallback). Si se quiere cambiar dinámicamente de proveedor (ej. Google AI Studio → Groq), hay que modificar código Python. La arquitectura actual no soporta acoplamiento/desacoplamiento dinámico de proveedores y modelos desde configuración.
  - **Discusión (2026-05-31):** Se evaluaron dos enfoques:
    1. **Plan Completo (Factory Pattern Asíncrono):** Refactorizar `engine.py` con una fábrica `_create_llm_by_provider(provider, model)` guiada por `.env`. Ventajas: desacoplamiento total, cualquier proveedor configurable sin tocar código. Desventajas: modifica 7+ archivos, riesgo de regresión, complejidad alta (posible over-engineering).
    2. **Plan Pragmático (Incremental):** Solo modificar lo necesario para habilitar la rotación de keys de Google AI Studio en `SemanticChunker` (2 archivos). Postergar la refactorización completa hasta que haya evidencia medible de necesidad (cambios frecuentes de proveedor).
  - **Decisión Pendiente:** ¿Cuándo refactorizar `engine.py` al Factory Pattern? Criterio objetivo: si en 6 meses hay 2+ cambios de proveedor en producción, se ejecuta el Plan Completo. Si no, se mantiene el Plan Pragmático.
  - **Dependencia:** RoundRobinKeyProvider (ya implementado, A.10), A.6 (reingesta con SemanticChunker)
  - (Pendiente — A Discutir ⏳)

---

## Bloque B: Expansión de Memoria y Contexto

### Objetivo

Convertir historiales externos en conocimiento estructurado.

### Justificación

La IA es más potente cuanta más información histórica posee del usuario para personalizar su estilo y recomendaciones.

### Tareas y Estado

- [ ] **B.1 Herramienta de Ingesta Masiva (Bulk Ingestor)**: Parsers para exportaciones de WhatsApp, Claude y ChatGPT. (Finalizado ✅ 2026-05-30 — WhatsAppParser, ClaudeParser, ChatGPTParser en src/tools/bulk_ingestor.py)
- [ ] **B.2 Agente de Revisión de Vida (Life Review)**: Análisis masivo para extraer hitos y valores del perfil. (Finalizado ✅ 2026-05-30 — run_life_review en src/agents/workers/life_review.py)
- [x] **B.3 Olvido Inteligente (Smart Decay)**: Algoritmo de Ranking con factor temporal. (Finalizado ✅ 2026-05-26 — ADR-0030, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Fase 1 Tarea 1.3)
- [x] **B.4 Arquitectura de Memoria Asociativa Multiresolución (Graph-RAG)**: Grafo relacional entre dominios, ingesta atómica de facts, RAG adaptativo y Two-Stage Retrieval. (Finalizado ✅ 2026-05-27 — ADRs 0029-0033, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Todas las fases completadas)
- [ ] **B.5 Aprendizaje de Aristas por Feedback**: Refuerzo y refinamiento de `memory_edges` basado en feedback implícito y explícito del usuario. El `ConsolidationWorker` ajusta pesos y crea/elimina aristas según la retroalimentación conversacional. (Finalizado ✅ 2026-05-30 — `_adjust_edge_weights_from_feedback` implementado)
- [ ] **B.6 Auditoría y Refactor del Sistema de Personalidad (Prioridad Máxima)**:
  - **Problema:** El prompt CBT incluye `CLINICAL_GUARDRAILS` que ordena al LLM mostrar recursos de crisis ante cualquier indicio. El usuario reporta respuestas repetitivas con "Línea 106" incluso cuando la mención fue metafórica ("apagarme"). No hay detección a nivel de código — solo confianza en el LLM.
  - **Solución:**
    1. Revisar los prompts de todas las skills (chat, tcc, psicotrading, transcription) para eliminar "basura" y mejorar naturalidad
    2. Implementar detección de crisis a nivel de código (keywords + análisis de sentimiento) antes de recurrir a guardrails LLM
    3. Hacer que los guardrails clínicos sean contextuales: que NO se activen por frases metafóricas
    4. Incorporar el sistema de archivos bootstrap de OpenClaw (IDENTITY.md, SOUL.md, USER.md inyectados)
    5. Permitir que la personalidad evolucione con feedback del usuario (re-escribir SOUL.md basado en interacciones)
    6. Verificar que el Soul Stack de 5 capas se está componiendo correctamente en los prompts
  - **Inspiración:** OpenClaw (archivos bootstrap + evolución de personalidad)
  - (Parcialmente implementado ✅ 2026-05-30 — crisis_detector.py a nivel de codigo con deteccion de metaforas)
- [ ] **B.7 Inteligencia Temporal y Análisis Temporal (Prioridad Máxima)**:
  - **Problema:** El sistema inyecta la hora local del usuario en el prompt (Layer 5 del Soul Stack), pero no tiene:
    1. Decaimiento temporal visible (el `MEMORY_DECAY_LAMBDA` afecta el ranking pero no se comunica al LLM)
    2. Conciencia de calendario (días festivos, estaciones, patrones semanales)
    3. Análisis de patrones temporales (ej. "los lunes estás más ansioso")
  - **Solución:**
    1. ✅ Agregar metadata temporal en hechos atómicos (día de semana, hora del día)
    2. ✅ Implementar detección de patrones temporales en el `ConsolidationWorker`
    3. ✅ Exponer al LLM la antigüedad de los hechos que está viendo
  - **Dependencia:** A.5 (facts atómicos → metadata temporal)
  - (Finalizado ✅ 2026-05-30 — metadata temporal + edad visible + patrones temporales)

---

## Bloque C: Ecosistema de Acción

### Objetivo

Dotar al asistente de capacidad real de acción mediante herramientas.

### Justificación

AEGEN debe pasar de ser un observador a ser un agente proactivo capaz de gestionar agenda y buscar información real.

### Tareas y Estado

- [x] **C.1 Fábrica de Habilidades**: Infraestructura de registro automático de herramientas y skills dinámicos. (Finalizado ✅ 2026-05-12) **→ PRERREQUISITO para Bloque D: auditar que esté operativo antes de implementar D.2.**
- [ ] **C.2 Integración de Herramientas**: Google Calendar, Búsqueda Web, Análisis de Archivos. (Finalizado ✅ 2026-05-30 — google_calendar.py, web_search.py)
- [ ] **C.3 Verificador de Verdad**: Proceso de auto-crítica contra la Bóveda de Conocimiento. (Finalizado ✅ 2026-05-30 — truth_verifier.py)
- [ ] **C.4 Graph-RAG Universal Data-Driven (Prioridad Máxima)**: La expansión de grafo debe activarse cuando existan datos relevantes, no cuando un intent analítico (que no existe) lo indique.
  - **Bug raíz (ver A.4):** Los intents analíticos hardcodeados en `context_retriever.py` no existen en `IntentType`. El Graph-RAG es código muerto.
  - **Solución:** Reemplazar la lógica de intents analíticos por un chequeo rápido de existencia de aristas: `SELECT 1 FROM memory_edges WHERE origen_id IN (...) OR destino_id IN (...) LIMIT 1`. La expansión usa siempre `max_hops=2` con poda por peso (>0.3) y límite de 8 fragmentos. Las aristas aprenden y evolucionan con feedback del ConsolidationWorker (ADR-0034 sección 1c).
  - **Verificación:** Una consulta cross-dominio (ej. "¿cómo afecta mi entrenamiento a mi estado de ánimo?") debe retornar fragmentos de al menos 2 dominios distintos conectados por `memory_edges`.
  - **Dependencia:** Requiere que `memory_edges` tenga datos (se genera en cada consolidacion, ~10 mensajes). Si no hay aristas, la expansion no se ejecuta y no hay penalizacion de latencia.
  - (Finalizado ✅ 2026-05-30 — Graph-RAG data-driven activado)
- [ ] **C.5 Observabilidad Completa para Auditoria (Prioridad Maxima)**:
  - **Problema:** La observabilidad actual tenia fallos criticos que impedian auditar si el sistema funciona correctamente.
  - **Solucion implementada:**
    1. ✅ Corregido `metrics_processor.py` para detectar todos los providers LLM
    2. ✅ Implementada estimacion de costos para todos los providers
    3. ✅ Integrado `estimate_cost_usd` en `update_metrics_from_result`
    4. ✅ Creado `RoundRobinKeyProvider` para rotacion de API keys
    5. ✅ Corregidos endpoints REST: timestamps reales, sin valores hardcodeados
    6. ⏳ Dashboard Prometheus + Grafana pendiente de configuracion en GCP
    7. ⏳ Alertas automaticas en `AdminNotificator` pendientes
  - (Parcialmente implementado ✅ 2026-05-30 — multi-provider + costos + round-robin + endpoints)

---

## Bloque D: Auto-mejora y Evolución del Sistema

### Objetivo

Implementar un bucle de aprendizaje continuo donde el sistema evolucione basado en la retroalimentación de las interacciones con el usuario, y sea capaz de crear nuevas habilidades dinámicamente según las necesidades detectadas. _Comentario: ESTO ES LO MAS IMPORTANTE, MUY MUY IMPORTANTE_

### Justificación

Los proyectos Hermes-agent (Nous Research, 172k⭐) y OpenClaw (375k⭐) han demostrado que los sistemas de IA más exitosos son aquellos que:

- Aprenden de cada interacción y se auto-mejoran (Hermes: curador automático, nudges de memoria/skills)
- Permiten crear nuevas habilidades dinámicamente según el uso (OpenClaw: Skill Workshop, creación de skills por el agente mismo)
- Tienen personalidad profunda que evoluciona con el usuario (OpenClaw: Soul Stack + archivos bootstrap)
- Son extensibles sin modificar el código base (OpenClaw: plugin system, AgentSkills format)

### Tareas y Estado

- [ ] **D.1 Bucle de Aprendizaje Continuo por Feedback (Prioridad Máxima)**:
  - **Inspiración:** Hermes-agent (https://github.com/NousResearch/hermes-agent)
  - **Objetivo:** El sistema debe mejorar con cada interacción del usuario, no solo almacenar datos.
  - **Componentes a implementar:**
    1. **Nudge de memoria post-turno:** Después de cada conversación, evaluar automáticamente si hay algo que recordar (preferencias, hechos, lecciones) y persistirlo sin intervención del usuario. Similar a Hermes-agent que revisa cada N turnos si debe guardar memoria.
    2. **Nudge de skills post-turno:** Si el usuario completa un workflow complejo (herramientas, consultas multi-paso), el sistema debe sugerir crear una skill para capturar ese procedimiento. Hermes-agent lo dispara cuando detecta 5+ tool calls en una tarea.
    3. **Curador automático de skills (Curator):** Worker en background (ejecución semanal) que:
       - Skills no usadas >30 días → marcarlas como `stale`
       - Skills no usadas >90 días → archivarlas (mover a `.archive/`)
       - Skills relacionadas → consolidarlas bajo un "paraguas"
       - El curador debe tener modo `--dry-run` que solo reporta sin mutar
    4. **Compresión de contexto por LLM:** Cuando la conversación se acerca al límite de tokens, usar un modelo auxiliar (Gemini Flash) para resumir el historial medio, protegiendo los primeros y últimos N mensajes. En lugar de truncar ciegamente.
    5. **Session search tool:** Implementar búsqueda full-text sobre conversaciones previas usando FTS5 (ya existe en `keyword_search.py`), expuesta como tool para que MAGI pueda consultar su propia historia.
     6. **Insights engine:** Dashboard de analítica de uso: modelos más usados, costos, skills más cargadas, tokens por sesión, patrones de actividad. (Finalizado ✅ 2026-05-30 — insights_engine.py)
  - **Archivos de referencia (Hermes-agent):** `agent/curator.py`, `agent/memory_manager.py`, `agent/context_compressor.py`, `agent/insights.py`
  - (Finalizado ✅ 2026-05-30 — nudge worker, session search, curador, compresor, insights)
- [ ] **D.2 Sistema de Skills Dinamicos Auto-generados (Prioridad Maxima)**:
  - **Inspiracion:** OpenClaw (https://github.com/openclaw/openclaw)
  - **Objetivo:** El sistema debe poder crear, modificar y eliminar skills basandose en las necesidades del usuario, sin intervencion manual del desarrollador.
  - **Componentes implementados:**
    1. ✅ **Skill Workshop (auto-creacion):** Implementado en `skill_workshop.py` con generate_skill_from_pattern, approve_skill, reject_skill.
    2. ✅ **Sistema de gating condicional:** Implementado en `skill_loader.py`.
    3. ✅ **Precedencia de carga multi-nivel:** Implementado en `SkillLoader` con storage/skills/user > storage/skills > src/personality/skills.
    4. ⏳ **Per-Agent allowlists:** Pendiente.
    5. ✅ **Skill watcher (hot reload):** Implementado en `KnowledgeWatcher`.
    6. ✅ **CLI de skills:** Implementado en `skills_cli.py` (list, create, install, status).
    7. ✅ **Formato SKILL.md estandar:** Soportado con campo `requires`.
    8. ⏳ **AEGEN Hub (futuro):** Pendiente.
  - **Archivos afectados:** `src/personality/skill_loader.py`, `src/core/schemas/skills.py`, `src/memory/knowledge_watcher.py`, `src/personality/skill_curator.py`, `src/personality/skill_workshop.py`, `src/tools/skills_cli.py`
  - **Archivos de referencia (OpenClaw):** Skill Workshop, sistema de gating, precedencia de carga, ClawHub
  - (Finalizado ✅ 2026-05-30 — gating + hot-reload + curador + workshop + CLI)

---

## Notas y Riesgos

- La transicion a memoria local-first requiere una gestion cuidadosa de las migraciones de SQLite.
- Los parsers externos (WhatsApp) son sensibles a cambios de formato de la plataforma.
- **Deuda tecnica de intents:** Los bugs BUG-1 a BUG-5 fueron corregidos.
- **Orden de ejecucion recomendado (ciclo actual):** A.5 → A.6 → A.7 → A.8 → A.9 (requieren GCP) → B.6 (completo: guardrails) → C.5 (dashboard + alertas) → D.2 (allowlists + AEGEN Hub).
- **Bloque D (Auto-mejora) implementado:** Nudge worker, session search, curador, compresor, edge feedback, insights, skill workshop, gating, hot-reload, CLI.
- **Bloqueantes externos (GCP):** A.5, A.6, A.7, A.8 y A.9 requieren acceso a la VM de GCP.
- **Principio de diseño de intents:** Los 11 valores de `IntentType` representan verbos, no temas. Ver ADR-0038.
- **Tests:** 206 tests pasando, 7 failures pre-existentes no relacionados.
