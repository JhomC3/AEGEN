# PLAN: Estratégico Maestro de Implementación (AEGEN)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** En Ejecución
- **Fecha:** 2026-02-12
- **Razón de Creación:** Planificación a largo plazo para la evolución del sistema AEGEN hacia la autonomía total.
- **Objetivo General:** Transformar AEGEN en un sistema de IA autónomo, profesional, con memoria persistente y capacidades de acción externa.

---

## Resumen Ejecutivo
Este plan maestro define la hoja de ruta técnica para AEGEN. Se divide en tres bloques fundamentales: Saneamiento (Bloque A), Expansión de Memoria (Bloque B) y Capacidad de Acción (Bloque C). Actualmente, el sistema ha completado el saneamiento estructural y se prepara para la fase de expansión masiva de contexto.

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
  - **Problema:** El `IntentType` enum (`src/core/routing_models.py`) define 10 intents. El `context_retriever.py` hardcodea 3 intents analíticos (`life_review`, `pattern_analysis`, `cross_domain_query`) para activar Graph-RAG. **Ninguno de esos 3 existe en el enum.** El Graph-RAG por intents analíticos es código muerto. Adicionalmente, `routing_tools.py` no incluye `psicotrading` en su Literal.
  - **Solución:** Eliminar la dependencia de intents para el Graph-RAG. Reemplazar por detección data-driven: si los fragmentos recuperados tienen aristas en `memory_edges`, expandir el grafo.
  - (Pendiente ⏳)
- [ ] **A.5 Migrar Facts Legacy a Atómicos en Producción (Prioridad Máxima)**:
  - **Problema:** 439 facts del usuario `6095416210` están en formato JSON blob (pre-ADR-0032). El RAG no puede encontrarlos semánticamente.
  - **Solución:** Ejecutar `make migrate-facts` en la VM de GCP para re-ingestar cada hecho como registro atómico individual con su propio embedding.
  - (En Ejecución 🔄)
- [ ] **A.6 Re-ingestar PDFs Globales con SemanticChunker (Prioridad Máxima)**:
  - **Problema:** Los PDFs en `storage/knowledge/` (TCC, DSM-5) fueron ingeridos con el chunker recursivo plano (400 tok). No tienen estructura jerárquica (Nivel 3 → Nivel 4) ni purificación de ruido.
  - **Solución:** Re-procesar los PDFs usando `use_semantic_chunker=True` en el `IngestionPipeline`. Esto generará chunks padres (Nivel 3) e hijos (Nivel 4) vinculados por `parent_id`, con contenido purificado de ruido.
  - **Verificación:** Los chunks existentes se marcan `is_active=0`. Los nuevos chunks reemplazan a los viejos. El RAG debe encontrar fragmentos semánticamente coherentes en lugar de texto partido a la mitad.
  - (Pendiente ⏳)
- [ ] **A.7 Activar Respaldo en GCS (Prioridad Máxima)**:
  - **Problema:** `GCS_BACKUP_BUCKET = None`. El `CloudBackupManager` es funcional pero nunca se activó. Si la VM se destruye, se pierden todos los datos.
  - **Solución:** 
    1. Crear bucket GCS (ej. `aegen-backups`) con retention policy de 30 días
    2. Configurar `GCS_BACKUP_BUCKET` y `GCS_CREDENTIALS_JSON` en el `.env` de la VM
    3. Verificar en logs que el backup se ejecuta tras cada consolidación
  - (Pendiente ⏳)
- [ ] **A.8 Snapshots Periódicos del Disco de la VM (Prioridad Alta)**:
  - **Problema:** Sin respaldo cloud, el disco de la VM es el único almacén. Un fallo del disco o un delete accidental de la VM destruye todo.
  - **Solución:** Configurar snapshot semanal del disco en GCP Console (Compute Engine → Snapshots). Retención de 4 semanas.
  - (Pendiente ⏳)
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
  - **Problema:** Los logs muestran uso de Minimax vía OpenRouter para CBT (3s, 6479 tokens). La auditoría revela que Minimax es solo el fallback de `get_analytical_llm()`, pero se activó porque Groq no respondió a tiempo o falló. Adicionalmente, no se están usando las API keys gratuitas de Google AI Studio disponibles.
  - **Solución:**
    1. Investigar por qué Groq falla para `get_analytical_llm()` y `get_fast_llm()` en producción
    2. Evaluar migrar `REASONING_MODEL` a Gemini Flash para eliminar dependencia de OpenRouter
    3. Configurar API keys de Google AI Studio en `.env` de GCP para aprovechar rate limits free
    4. Si se confirma Gemini como analytical LLM, actualizar `ADR-0027` (Inteligencia Asimétrica)
  - (Pendiente ⏳)

---

## Bloque B: Expansión de Memoria y Contexto
### Objetivo
Convertir historiales externos en conocimiento estructurado.

### Justificación
La IA es más potente cuanta más información histórica posee del usuario para personalizar su estilo y recomendaciones.

### Tareas y Estado
- [ ] **B.1 Herramienta de Ingesta Masiva (Bulk Ingestor)**: Parsers para exportaciones de WhatsApp, Claude y ChatGPT. (Pendiente ⏳)
- [ ] **B.2 Agente de Revisión de Vida (Life Review)**: Análisis masivo para extraer hitos y valores del perfil. (Pendiente ⏳)
- [x] **B.3 Olvido Inteligente (Smart Decay)**: Algoritmo de Ranking con factor temporal. (Finalizado ✅ 2026-05-26 — ADR-0030, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Fase 1 Tarea 1.3)
- [x] **B.4 Arquitectura de Memoria Asociativa Multiresolución (Graph-RAG)**: Grafo relacional entre dominios, ingesta atómica de facts, RAG adaptativo y Two-Stage Retrieval. (Finalizado ✅ 2026-05-27 — ADRs 0029-0033, Plan `2026-05-26-arquitectura-memoria-asociativa-v090.md`, Todas las fases completadas)
- [ ] **B.5 Aprendizaje de Aristas por Feedback**: Refuerzo y refinamiento de `memory_edges` basado en feedback implícito y explícito del usuario. El `ConsolidationWorker` ajusta pesos y crea/elimina aristas según la retroalimentación conversacional. (Pendiente ⏳)
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
  - (Pendiente ⏳)
- [ ] **B.7 Inteligencia Temporal y Análisis Temporal (Prioridad Máxima)**:
  - **Problema:** El sistema inyecta la hora local del usuario en el prompt (Layer 5 del Soul Stack), pero no tiene:
    1. Duración de la sesión en el prompt (MAGI no sabe cuánto lleva hablando)
    2. Decaimiento temporal visible (el `MEMORY_DECAY_LAMBDA` afecta el ranking pero no se comunica al LLM)
    3. Conciencia de calendario (días festivos, estaciones, patrones semanales)
    4. Análisis de patrones temporales (ej. "los lunes estás más ansioso")
  - **Solución:**
    1. Inyectar duración de sesión en el contexto runtime
    2. Agregar metadata temporal en hechos atómicos (día de semana, hora del día)
    3. Implementar detección de patrones temporales en el `ConsolidationWorker`
    4. Exponer al LLM la antigüedad de los hechos que está viendo
  - **Dependencia:** A.5 (facts atómicos → metadata temporal)
  - (Pendiente ⏳)

---

## Bloque C: Ecosistema de Acción
### Objetivo
Dotar al asistente de capacidad real de acción mediante herramientas.

### Justificación
AEGEN debe pasar de ser un observador a ser un agente proactivo capaz de gestionar agenda y buscar información real.

### Tareas y Estado
- [x] **C.1 Fábrica de Habilidades**: Infraestructura de registro automático de herramientas y skills dinámicos. (Finalizado ✅ 2026-05-12)
- [ ] **C.2 Integración de Herramientas**: Google Calendar, Búsqueda Web, Análisis de Archivos. (En Curso 🔄)
- [ ] **C.3 Verificador de Verdad**: Proceso de auto-crítica contra la Bóveda de Conocimiento. (Pendiente ⏳)
- [ ] **C.4 Graph-RAG Universal Data-Driven (Prioridad Máxima)**: La expansión de grafo debe activarse cuando existan datos relevantes, no cuando un intent analítico (que no existe) lo indique.
  - **Bug raíz (ver A.4):** Los intents analíticos hardcodeados en `context_retriever.py` no existen en `IntentType`. El Graph-RAG es código muerto.
  - **Solución:** Reemplazar la lógica de intents analíticos por un chequeo rápido de existencia de aristas: `SELECT 1 FROM memory_edges WHERE origen_id IN (...) LIMIT 1`. Esto cuesta <5ms si no hay aristas, ~50-150ms si las hay. El costo marginal es trivial comparado con el tiempo de respuesta total (~7s).
  - **Verificación:** Una consulta cross-dominio (ej. "¿cómo afecta mi entrenamiento a mi estado de ánimo?") debe retornar fragmentos de al menos 2 dominios distintos conectados por `memory_edges`.
  - **Dependencia:** Requiere que `memory_edges` tenga datos (se genera en cada consolidación, ~10 mensajes). Si no hay aristas, la expansión no se ejecuta y no hay penalización de latencia.
  - (Pendiente ⏳ — Ver plan detallado en `docs/planes/2026-MM-DD-graph-rag-universal.md`)
- [ ] **C.5 Observabilidad Completa para Auditoría (Prioridad Máxima)**:
  - **Problema:** La observabilidad actual tiene fallos críticos que impiden auditar si el sistema funciona correctamente:
    1. `metrics_processor.py` solo detecta `ChatGoogleGenerativeAI` — Groq y OpenRouter aparecen como `provider="unknown"`
    2. Los costos solo se estiman para Gemini; Groq/OpenRouter no se contabilizan
    3. Los endpoints `/system/llm/metrics/summary` tienen valores hardcodeados (latencia 0.0)
    4. No existe dashboard para visualizar métricas en tiempo real
    5. No hay alertas automáticas cuando un componente falla
  - **Solución:**
    1. Corregir `metrics_processor.py` para detectar todos los providers LLM
    2. Implementar estimación de costos para Groq y OpenRouter
    3. Eliminar valores hardcodeados de los endpoints REST
    4. Configurar Prometheus + Grafana (o Google Cloud Monitoring) para dashboard en tiempo real
    5. Implementar alertas en el `AdminNotificator` para fallos de componentes críticos
  - (Pendiente ⏳)

---

## Bloque D: Auto-mejora y Evolución del Sistema

### Objetivo
Implementar un bucle de aprendizaje continuo donde el sistema evolucione basado en la retroalimentación de las interacciones con el usuario, y sea capaz de crear nuevas habilidades dinámicamente según las necesidades detectadas.

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
    6. **Insights engine:** Dashboard de analítica de uso: modelos más usados, costos, skills más cargadas, tokens por sesión, patrones de actividad.
  - **Archivos de referencia (Hermes-agent):** `agent/curator.py`, `agent/memory_manager.py`, `agent/context_compressor.py`, `agent/insights.py`
  - (Pendiente ⏳)
- [ ] **D.2 Sistema de Skills Dinámicos Auto-generados (Prioridad Máxima)**:
  - **Inspiración:** OpenClaw (https://github.com/openclaw/openclaw)
  - **Objetivo:** El sistema debe poder crear, modificar y eliminar skills basándose en las necesidades del usuario, sin intervención manual del desarrollador.
  - **Componentes a implementar:**
    1. **Skill Workshop (auto-creación):** Implementar un mecanismo donde MAGI pueda crear nuevos SKILL.md en `src/personality/skills/` mediante tool calls, capturando procedimientos observados. Ejemplo: si el usuario ingresa datos de gimnasio sistemáticamente, MAGI puede crear una skill "fitness_tracker" para manejar esos datos.
    2. **Sistema de gating condicional:** Skills que se cargan solo cuando se cumplen condiciones específicas:
       - `requires.bins`: binarios en PATH
       - `requires.python_packages`: paquetes Python instalados
       - `requires.env`: variables de entorno configuradas
       - `requires.config`: configuraciones específicas
       - `os`: filtro por plataforma
    3. **Precedencia de carga multi-nivel:** Workspace > Project > Personal > Bundled. Skills en niveles superiores sobreescriben a los inferiores. Esto permite a los usuarios personalizar skills sin modificar las bundled.
    4. **Per-Agent allowlists:** Cada skill/agente debe poder tener su propia lista blanca de skills activas, definida en configuración.
    5. **Skill watcher (hot reload):** Extender el `KnowledgeWatcher` existente para que también observe cambios en `src/personality/skills/` y recargue skills automáticamente sin reiniciar.
    6. **CLI de skills:** Comandos como `aegen skills install <name>`, `aegen skills list`, `aegen skills create` para gestionar skills desde terminal.
    7. **Formato SKILL.md estándar:** Adoptar completamente el formato AgentSkills (frontmatter YAML + Markdown) compatible con `agent-skills.io`.
    8. **AEGEN Hub (futuro):** Registro centralizado de skills donde la comunidad pueda compartir habilidades.
  - **Archivos afectados:** `src/personality/skill_loader.py`, `src/personality/skill_parser.py`, `src/personality/manager.py`, `src/memory/knowledge_watcher.py`, nuevo `src/personality/skill_workshop.py`
  - **Archivos de referencia (OpenClaw):** Skill Workshop, sistema de gating, precedencia de carga, ClawHub
  - (Pendiente ⏳)

---

## Notas y Riesgos
- La transición a memoria local-first requiere una gestión cuidadosa de las migraciones de SQLite.
- Los parsers externos (WhatsApp) son sensibles a cambios de formato de la plataforma.
