# Especificación de Arquitectura: Eficiencia de Tokens, Cerebro Virtual y Graph-RAG Dinámico

- **Fecha:** 22 de Mayo de 2026
- **Autores:** Lead Architect & MAGI AI
- **Estado:** Aceptado (Base de Diseño de Producción) — Revisado con Auditoría Técnica Completa (26 de Mayo de 2026)

---

## 1. Definición del Problema y Radiografía de Ineficiencia

El sistema de memoria original de AEGEN experimentó fallos de estabilidad en producción (Google Cloud VM), manifestados en errores `413 Request too large` (Rate Limit de 8,000 Tokens Por Minuto en Groq `gpt-oss-120b`). Estos fallos son el síntoma de una ineficiencia estructural en tres capas:

### A. Ingesta de Fuerza Bruta Lineal

- **El Bug:** El chunker tradicional (`src/memory/chunker.py`, 400 tok / 80 overlap, `tiktoken cl100k_base`) corta textos clínicos y transcripciones de YouTube a bloques lineales rígidos sin criterio semántico.
- **Consecuencia:** Se almacenan y vectorizan muletillas (*"suscríbete al canal"*, *"eh..."*), números de página y frases rotadas por la mitad. Al buscar, se inyecta "basura" cruda que satura la ventana de tokens sin aportar valor terapéutico real.
- **Corrección de Causalidad (Auditoría):** El error `413` de Groq NO es causado por el tamaño de un request individual del chunker. Es un error de Rate Limit de 8,000 Tokens Por Minuto. La causa real es que `MemorySummarizer` y `EvolutionDetector` usan el modelo global de Groq (`gpt-oss-120b`) en procesos de background concurrentes, agotando la cuota TPM acumulada en conversaciones largas. El chunker es un problema de *calidad semántica*; los modelos de consolidación son la causa de la *inestabilidad de producción*. Ambos deben corregirse, pero son bugs independientes con soluciones distintas.

### B. Recuperación Estática (El RAG Rígido)

- **El Bug:** La herramienta de TCC (`src/personality/skills/tcc/tools.py`) recupera siempre 3 fragmentos globales y 2 de usuario, con límites hardcoded sin diferenciar el intent del mensaje ni filtrar por `memory_type`.
- **Consecuencia:** Incluso si el usuario envía un mensaje casual de saludo (*"Hola, ¿cómo estás?"*), el RAG inyecta de 1,000 a 2,000 tokens innecesarios de teoría clínica en el prompt de sistema del especialista. Agravante: el RAG recupera indistintamente `fact`, `conversation`, `document` y logs de sesión serializados como JSON, contaminando el contexto con datos irrelevantes.
- **Inconsistencia Detectada:** Los pesos de RRF (`vw=0.7, kw=0.3`) y los límites de fragmentos están hardcodeados en cada tool de cada especialista, creando inconsistencias entre Chat y CBT sin posibilidad de ajuste centralizado.

### C. Ruido Cognitivo por Crecimiento de Hechos (`structured_knowledge`)

- **El Bug:** El extractor de hechos serializa el diccionario completo de la bóveda como un blob JSON masivo y lo pasa al `IngestionPipeline`, que lo chunquea junto. Al buscar "prefiere café" se puede recuperar un chunk de 400 tokens de JSON mezclado que el LLM debe parsear mentalmente. No hay ingesta atómica por fact individual.
- **Consecuencia:** Con los meses, el JSON acumula hechos viejos irrelevantes o contradictorios (*"Usuario estresado por Proyecto X"* vs *"Usuario completó con éxito el Proyecto X"*), saturando el prompt con datos desactualizados.
- **Inconsistencia Detectada (Gap Crítico):** El documento original de v0.7.0 afirma que el Time Decay está implementado ("Las memorias recientes reciben un impulso en el ranking"). Sin embargo, la auditoría del código confirma que `hybrid_search.py` aplica RRF puro sin considerar `created_at`. El Time Decay está documentado pero no implementado. Esta deuda genera el ruido temporal descrito.

---

## 2. La Solución Arquitectónica Elegida (Los Tres Pilares)

Para construir un sistema cognitivo de nivel mundial que sea estable en Groq (8k TPM)_Comentario: el objetivo no es que sea estable en groq, si buscando que groq pueda manejar las solicitudes se descubrio que debemos buscar eficiencia y eficacia, lo cual si es el objetivo independientemente del proveedor o modelo de llm_, soporte transcripciones masivas de canales de YouTube y libros, y entregue una comprensión profunda del usuario, se adopta de forma integrada la siguiente **Arquitectura de Memoria Asociativa Multiresolución (Obsidian-like)**:

```text
                  ┌────────────────────────────────────────┐
                  │   Pilar I: Semantic Ingestion (LLM)    │
                  │   Destila & clasifica en 4 Niveles     │
                  │   + Ingesta Atómica de Facts           │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Pilar III: Cerebro Virtual (SQLite)  │
                  │   Grafo Relacional + Notas Evolutivas  │
                  │   + Two-Stage Retrieval con Time Decay │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Pilar II: RAG Dinámico (Redis+SQL)   │
                  │   Caché Evolutivo -> GraphRAG          │
                  │   -> Rerank API -> GraphStateV2        │
                  └────────────────────────────────────────┘
```

---

### Pilar I: Ingesta Jerárquica Multinivel Asistida por Destilación

Descartamos la ingesta por fuerza bruta. El nuevo estándar de ingesta se estructura en una **Red Jerárquica Multinivel (Cerebro Virtual)**. Dado que la información proviene de orígenes fundamentalmente distintos, la arquitectura implementa una bifurcación ontológica estricta:

1. **Ingesta Asíncrona Diferenciada:**
   - **Fuentes Externas (Libros, YouTube):** Un agente ligero (Gemini Flash, no Flash-Lite — se prefiere Flash por su ventana de contexto mayor para libros completos)_Comentario: el modelo es lo de menos, si bien es importante tener en cuenta la ventana de contexto, el modelo puede ser facilmente sustituido por cualquiero otro, por lo tanto el metodo de chunks debe poderse adaptar_ purifica el texto entrante, elimina ruido y aplica formato estructurado antes de guardar. Para controlar el costo por token en documentos masivos, el pipeline aplicará primero un pre-filtro heurístico (stop-words, expresiones de canal, marcas de tiempo) que reduce el texto bruto antes de enviarlo al LLM. En un libro de 300 páginas esto representa ~750 chunks × 1 llamada LLM a Gemini Flash — un costo estimado y aceptable que debe monitorizarse con la métrica `ingestion_llm_calls_total`.
   - **Fuentes Internas (Chat del Usuario):** Los mensajes se guardan en el búfer de forma inmediata (cruda) para garantizar 0 latencia en la interacción de Telegram. Es el proceso en background del Pilar III el que posteriormente los destila y clasifica.

2. **Doble Ontología Jerárquica:**
   - **Ontología Semántica (Fuentes Externas):**
     - Nivel 1: Conceptos Clínicos Universales (ej. Terapia Cognitiva).
     - Nivel 2: Marcos Teóricos (ej. Distorsiones Cognitivas).
     - Nivel 3: Técnicas (ej. Reestructuración).
     - Nivel 4: Fragmentos purificados del libro o video.
     _Coemntario: Estons niveles no son solo para contenido de psicolgia clinica, deben ser aptos para cualquier tipo de contenido, Finanzas, nutrición, deporte, entrenamiento, educación, etc..._
   - **Ontología Episódica (Fuentes Internas):**
     - Nivel 1: Macro-narrativa de Vida (Línea de tiempo general y estado global).
     - Nivel 2: Áreas de Vida Agnósticas (Psicología, Finanzas, Fitness, Nutrición).
     - Nivel 3: Patrones y Rutinas (ej. Hábitos matutinos, Presupuesto mensual, Progresión de cargas).
     - Nivel 4: Eventos Atómicos y Métricas (ej. Mensaje de ánimo, Gasto: $50 en café, Entrenamiento: Sentadilla 100kg, Calorías: 2000kcal).

3. **Ingesta Atómica de Facts (Corrección del Gap Crítico):**
   - **El problema eliminado:** `knowledge_base_manager.save_knowledge()` serializa el dict completo como un blob JSON y lo pasa al `IngestionPipeline`, que lo chunquea en bloques de 400 tokens mezclando múltiples hechos distintos. El resultado es que buscar un fact recupera un chunk ruidoso de JSON.
   - **La solución:** Cada hecho extraído por `FactExtractor` se ingesta como un registro independiente en la tabla `memories` con su propio embedding, su propio `domain`, `hierarchy_level=4`, y sus propios metadatos Pydantic. La búsqueda vectorial recupera hechos precisos, no bloques de JSON.

4. **Mapeo Relacional Transversal (Grafo Verdadero):** Además de la relación jerárquica (`parent_id`), el pipeline utilizará una tabla adicional `memory_edges` (`origen_id`, `destino_id`, `tipo_relacion`) para establecer asociaciones directas entre distintos dominios, materializando el Graph-RAG.

---

### Pilar II: RAG Adaptativo, Tiempo y Recuperación Cognitiva

Rechazamos los umbrales matemáticos rígidos y los cachés de respuesta estática. El motor de recuperación debe poseer conciencia temporal y adaptabilidad clínica:

1. **Caché del Estado Cognitivo Unificado (Redis):**
   - *Corrección de Arquitectura:* Un caché semántico tradicional de "respuesta exacta" es inútil terapéuticamente. MAGI no puede responder siempre igual ante la misma queja.
   - *La Solución:* Redis almacenará el **Estado Cognitivo Pre-calculado** (la Nota Evolutiva generada por el Pilar III) extendiendo la clave existente `chat:summary:{chat_id}`. Cuando el usuario habla, MAGI accede a esta nota en Redis con latencia de 0ms, obteniendo la foto temporal exacta y la evolución del usuario sin consultar SQLite, unificando la evolución a largo plazo con la velocidad de memoria a corto plazo.
   - *Resiliencia:* Si Redis reinicia o la clave expira (TTL de 24h), el sistema reconstruye la nota desde SQLite en la siguiente consolidación. No hay pérdida de datos — solo degradación temporal de latencia. La reconvergencia es automática.

2. **Graph-RAG Relacional (Análisis Transversal):**
   - El buscador recupera sub-grafos relacionales que conectan múltiples dominios mediante la tabla `memory_edges` (ej. *Déficit calórico → incrementa → Irritabilidad → dispara → Gasto impulsivo*). Esto dota a MAGI de razonamiento analítico "multi-salto", cruzando métricas duras con variables blandas.
   - *Límite de profundidad:* Las queries de grafo se limitarán a **2 saltos máximo** mediante CTEs recursivos en SQLite. Profundidad mayor requeriría un motor de grafo dedicado y degradaría la latencia con 100K+ memorias.

3. **Filtro Rígido Pre-Búsqueda y Jerarquía Dinámica:**
   - La estructura de metadatos será obligatoria y validada por Pydantic: `{"domain": "fitness", "hierarchy_level": 3, "timestamp": 1716382910}`. Esto permite aplicar un filtro SQL `WHERE domain=? AND hierarchy_level=?` previo a la consulta vectorial en `sqlite-vec`, reduciendo el espacio de búsqueda antes del KNN.
   - Preguntas macro traen el resumen Nivel 1. Preguntas micro apuntan al Nivel 4. El tamaño del contexto inyectado se adapta al tipo de consulta.
   - *Nota sobre eficiencia del filtro:* El beneficio del filtro pre-búsqueda es proporcional a la selectividad del dominio. Si un usuario tiene pocos registros en `fitness`, el filtro aporta menos. Con mayor volumen de datos (>1000 memorias por dominio), el ahorro computacional es significativo.

4. **Reranker Semántico Basado en API:**
   - *Corrección de Arquitectura:* No se utilizará un cross-encoder local. Los modelos locales de reranking de calidad (ej. `ms-marco-MiniLM-L-12-v2`) requieren ~400MB de RAM y 50-200ms de inferencia en CPU, contradiciendo el objetivo de latencia sub-segundo en Telegram.
   - *La Solución:* Se implementará el reranking mediante una llamada al LLM disponible (Gemini Flash) con un prompt estructurado que evalúe la relevancia de cada fragmento candidato respecto a la pregunta actual. El reranker opera sobre el sub-grafo recuperado (Top-15 a 20 fragmentos) y selecciona los Top-5 finales para inyección, garantizando coherencia semántica sin overhead operacional de modelo local.

5. **Exposición del RAG al Orquestador (Corrección de Gap Crítico):**
   - *El problema eliminado:* Actualmente, el contexto RAG (`knowledge_context`, `history_summary`, `structured_knowledge`) se calcula dentro de cada tool de cada especialista y no se expone en `GraphStateV2`. El orquestador no puede auditarlo, limitarlo ni reutilizarlo. Si dos especialistas en cadena necesitan el mismo contexto, se recupera dos veces.
   - *La Solución:* Se añadirá un campo `rag_context: RagContextSnapshot | None` a `GraphStateV2`. Un nodo dedicado `context_retriever` ejecutará la recuperación *antes* del nodo especialista, depositando el resultado en el estado del grafo. Los especialistas consumen el contexto del estado, sin llamadas duplicadas a SQLite.

---

### Pilar III: Consolidación Evolutiva Temporal

El conocimiento episódico del usuario no debe acumularse infinitamente en un JSON plano. Se adopta un modelo de consolidación temporal que delega el cómputo pesado a background:

1. **Two-Stage Retrieval (Motor Matemático Híbrido — Implementación del Time Decay Real):**
   - *El Problema Técnico:* `sqlite-vec` es extremadamente rápido para buscar similitud pura, pero no permite inyectar fórmulas matemáticas de tiempo en su motor interno. El RRF actual ignora `created_at`.
   - *La Solución:* (Fase 1) SQLite devuelve los Top-100 resultados por similitud semántica pura via `sqlite-vec`. (Fase 2) En Python, se aplica la fórmula de decaimiento exponencial a esos 100 resultados:

     $$Score_{final} = Similitud \times e^{-\lambda \cdot \Delta t}$$

     donde $\Delta t$ es la antigüedad en días y $\lambda$ es el parámetro de decaimiento. El valor inicial de $\lambda$ será **0.01** (vida media ~70 días), calibrado empíricamente en los primeros meses con métricas de relevancia. Se expondrá como parámetro configurable en `settings`. Los Top-10 a 15 resultados de mayor `Score_final` se entregan al agente como contexto temporalmente priorizado.

2. **El Motor Cognitivo (Notas de Evolución Multidisciplinar mediante LLM en Background):**
   - El agente de consolidación lee esos eventos atómicos filtrados (sean financieros, físicos o emocionales) y redacta una **Nota de Progreso Analítica de Nivel 1/2**. Esta misma nota se propaga al caché de Redis del Pilar II.
   - *Corrección de Modelo (Gap Crítico):* `MemorySummarizer` y `EvolutionDetector` actualmente usan el modelo global Groq `gpt-oss-120b`, causando los errores `413` de producción. Ambos se migrarán a **Gemini Flash** (o Gemini Flash-Lite para operaciones más ligeras)_Comentario: Esto debe quedar de tal forma que se pueda elegir el modelo apropiado no necesariamente tiene que ser gemini, se deben poder hacer pruebas para elegir el idoneo_, liberando completamente la cuota de Groq para las respuestas conversacionales en tiempo real — que son la experiencia visible del usuario.
   - *Ejemplo de Evolución:* En lugar de inyectar 30 reportes diarios aislados, MAGI solo lee una nota estructurada: *"El usuario ha mantenido un déficit calórico constante durante 3 semanas... sin embargo, esto ha correlacionado con una desviación en su presupuesto"*.

3. **Recolección de Basura Cognitiva (Garbage Collection):**
   - A medida que el agente de consolidación crea nuevas narrativas en Niveles 1 y 2, tiene la capacidad de aplicar un *Soft Delete* (`is_active = 0`) a los vectores atómicos del Nivel 4 que ya han sido asimilados o resueltos. Esto previene el crecimiento infinito de la base de datos y mantiene las consultas vectoriales rápidas y puras.
   - El campo `is_active` ya existe en el schema (`schema.sql`) e índice (`idx_memories_active`). Solo se requiere implementar la lógica de decisión en el worker de consolidación.

---

## 3. Resolución de Deuda Técnica Sistémica (Gaps de Auditoría)

La auditoría del codebase actual (`v0.8.4`) identificó inconsistencias heredadas que bloquean o degradan la nueva arquitectura. Todas deben resolverse antes o durante la implementación de los Pilares:

### Gap 1 — Caché de Embeddings Inoperativa
- **Archivo:** `src/memory/schema.sql:61-65` (tabla definida), `src/memory/embeddings.py` (sin uso de caché).
- **Problema:** La tabla `embedding_cache` existe en el schema pero `EmbeddingService` nunca la consulta antes de llamar a la API de Google. Cada re-embedding de contenido idéntico incurre en costo de API innecesario.
- **Solución:** Implementar lógica hit/miss en `EmbeddingService.embed_query()` y `embed_documents()`: consultar `embedding_cache` por `content_hash` antes de llamar a la API; escribir el resultado tras cada llamada exitosa. Ahorro directo en costos de API durante re-ingestas y búsquedas repetidas.

### Gap 2 — RAG Invisible al Orquestador (LangGraph)
- **Archivo:** `src/core/schemas/graph.py:44-51` (`GraphStateV2` sin campo RAG), `src/personality/skills/chat/tools.py:93-110`, `src/personality/skills/tcc/tools.py:28-65`.
- **Problema:** El contexto RAG se calcula dentro de cada tool sin exponerse al estado del grafo. El orquestador no puede auditarlo. Si hay cadena de agentes, SQLite se consulta N veces.
- **Solución:** Añadir `rag_context: RagContextSnapshot | None` a `GraphStateV2`. Crear nodo `context_retriever` en el grafo LangGraph que ejecute la recuperación RAG antes del nodo especialista y deposite el snapshot en el estado. Requiere ADR por modificación de schema de estado.

### Gap 3 — Time Decay Documentado pero No Implementado
- **Archivo:** `src/memory/hybrid_search.py:86-95`.
- **Problema:** La documentación de v0.7.0 afirma que el Time Decay está implementado. El código aplica RRF puro sin considerar `created_at`. Las memorias de hace años compiten con igualdad frente a las de ayer.
- **Solución:** Implementar el Two-Stage Retrieval del Pilar III. Este gap ya tiene solución definida en la arquitectura; se documenta aquí como deuda confirmada a saldar.

### Gap 4 — Código Muerto: `session_processor.py`
- **Archivo:** `src/memory/session_processor.py` (~84 líneas).
- **Problema:** `SessionProcessor` implementa un flujo de consolidación alternativo (LLM extrae puntos clave → IngestionPipeline) que no tiene ningún caller activo en el codebase. El flujo activo es `ConsolidationManager`. Este archivo genera confusión sobre cuál es el pipeline canónico.
- **Solución:** Eliminar `session_processor.py`. Antes de eliminar, ejecutar `grep -r 'session_processor\|SessionProcessor' src/` para confirmar cero referencias. No requiere ADR.

### Gap 5 — Fallback Frágil de la Bóveda de Conocimiento
- **Archivo:** `src/memory/knowledge_base.py:59-75`.
- **Problema:** El fallback a SQLite ejecuta `search_by_type(memory_type="fact", limit=1, chat_id=chat_id)`, devolviendo máximo 1 registro y asumiendo que contiene el JSON completo de la bóveda. Pero la bóveda se guarda vía `IngestionPipeline` que la chunquea. El registro recuperado puede ser un fragmento parcial, sirviendo bóvedas incompletas silenciosamente.
- **Solución:** Migrar a ingesta atómica de facts (Gap 7/Pilar I). Con hechos individuales en vez de blobs, el fallback deja de depender de un único registro. Alternativamente, añadir una clave de metadatos `is_knowledge_vault_root: true` al registro raíz para recuperarlo unívocamente mientras se implementa la solución definitiva.

### Gap 6 — Namespaces Rotos: Todos los Usuarios Comparten `"user"`
- **Archivo:** `src/memory/ingestion_pipeline.py:36`, `src/memory/repositories/memory_repo.py:21`.
- **Problema:** El schema documenta `'global' | 'user_{id}'` pero el código hardcodea `namespace="user"` para todo contenido de usuario. El aislamiento real depende solo del `chat_id`, no del namespace. Si en el futuro se implementan queries por namespace, todos los usuarios colisionarían.
- **Solución:** Cambiar el default en `IngestionPipeline.process_text()` para aceptar y propagar `namespace=f"user_{chat_id}"` cuando se ingesta contenido de usuario. Requiere migration script para actualizar registros existentes en la columna `namespace`.

### Gap 7 — Ingesta de Facts como JSON Blob (No Atómica)
- **Archivo:** `src/memory/knowledge_base.py:96-107`, `src/memory/ingestion_pipeline.py:29-112`.
- **Problema:** `knowledge_base_manager.save_knowledge()` serializa el dict completo de hechos y lo pasa al chunker. Un chunk de 400 tokens puede contener 5-10 hechos distintos mezclados. Al buscar un hecho específico, se recupera ruido de hechos no relacionados.
- **Solución:** Implementar `save_knowledge_atomic()` que itera cada hecho del dict y llama a `IngestionPipeline.process_text()` individualmente, con metadatos `{"domain": ..., "fact_key": ..., "hierarchy_level": 4}`. Cada hecho tiene su propio embedding y es recuperable de forma precisa.

### Gap 8 — Modelos de Consolidación Usan Groq (Causa Raíz del 413)
- **Archivo:** `src/memory/consolidation_worker.py:18`, `src/memory/services/memory_summarizer.py:64`.
- **Problema:** `MemorySummarizer` y `EvolutionDetector` usan `llm` global (Groq `gpt-oss-120b`). En conversaciones activas, estos procesos de background compiten con las respuestas conversacionales por la cuota de 8K TPM de Groq, provocando los errores `413`.
- **Solución:** Migrar ambos a `get_rag_llm()` (Gemini Flash-Lite) o a `get_analytical_llm()` según la complejidad de la tarea. La cuota de Groq queda reservada exclusivamente para respuestas conversacionales en tiempo real, que son el path crítico de experiencia de usuario.

### Gap 9 — Sin Smart Decay / Olvido Inteligente
- **Estado:** Pendiente en Plan Maestro Estratégico (B.3).
- **Problema:** Las memorias nunca caducan. Con el tiempo, la base de datos crece indefinidamente y el RRF trae memorias de años con el mismo peso que las recientes.
- **Solución:** El Two-Stage Retrieval del Pilar III implementa el decaimiento temporal. El Garbage Collection del Pilar III implementa el olvido estructural mediante Soft Delete. Este gap queda cubierto por la nueva arquitectura.

### Gap 10 — `source_skill` Nunca Se Escribe en Ingesta
- **Archivo:** `src/memory/ingestion_pipeline.py:92-100` (sin `source_skill`), `src/memory/schema.sql:21` (columna definida).
- **Problema:** La columna `source_skill` existe en el schema y en `KeywordSearch` como filtro disponible, pero `IngestionPipeline.process_text()` nunca la popula. El filtro por skill origen es inoperable.
- **Solución:** Añadir parámetro `source_skill: str | None = None` a `IngestionPipeline.process_text()`. Todos los callers que ya conocen el skill origen (tools de CBT, Chat, Transcripción) deben pasarlo. Habilita el filtrado de memorias por especialista en el RAG.

### Gap 11 — RAG No Filtra por `memory_type` en Recuperación Genérica
- **Archivo:** `src/memory/vector_memory_manager.py:29-48`, `src/personality/skills/chat/tools.py:25-61`.
- **Problema:** `retrieve_context()` soporta filtrar por `context_type` pero los tools de Chat y CBT no lo usan. Se recuperan indistintamente `fact`, `conversation`, `document` y logs de sesión serializados como JSON, contaminando el contexto.
- **Solución:** Los tools de cada especialista deben pasar `context_type=["fact", "document"]` para recuperación de conocimiento base, y `context_type=["conversation"]` separadamente si necesitan historial episódico. La mezcla de tipos en una sola consulta debe eliminarse.

### Gap 12 — `embedding_cache` en Schema: Tabla Definida, Índice Ausente
- **Archivo:** `src/memory/schema.sql:61-65`.
- **Problema:** La tabla `embedding_cache` no tiene índice sobre `content_hash` pese a que toda la lógica de lookup será por ese campo. Sin índice, el lookup es O(n) sobre toda la tabla.
- **Solución:** Añadir `CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash ON embedding_cache(content_hash)` en `migration.py` junto con la implementación del Gap 1.

---

## 4. Consideraciones de Implementación

- **Estructura DB (Grafo):** La tabla `memories` adoptará el campo opcional `parent_id INTEGER REFERENCES memories(id)` para profundidad jerárquica, y se creará la tabla `memory_edges` (`id`, `origen_id`, `destino_id`, `tipo_relacion`, `peso REAL DEFAULT 1.0`, `created_at`) para las conexiones transversales (Graph-RAG verdadero).
- **Esquema de Metadatos:** Será estrictamente tipado y validado por Pydantic, garantizando que todo recuerdo ingrese con `domain` (string, enum de dominios válidos), `hierarchy_level` (int 1-4) y `timestamp` (Unix epoch) para filtrado SQL optimizado.
- **Mitigación de Riesgos de Rendimiento:** La separación del *Two-Stage Retrieval* y el traslado del análisis cognitivo pesado a procesos asíncronos en background (con modelos Gemini, no Groq) asegura que la experiencia del usuario final en Telegram se mantenga por debajo del segundo de latencia.
- **Obligatoriedad de ADR:** Toda modificación a la tabla `memories` (adición de `parent_id`) y la creación de `memory_edges` requieren un ADR previo según las reglas de `AGENTS.md`, ya que modifican el schema core de persistencia.
- **Migración de Datos Existentes:** La adición de `parent_id` y los metadatos obligatorios (`domain`, `hierarchy_level`) implica que las memorias existentes tendrán estos campos como `NULL`. Se requiere un script de migración one-shot que clasifique retroactivamente las memorias activas por `memory_type` y `source_type`, asignando defaults razonables (`hierarchy_level=4`, `domain="general"`) para mantener el sistema operativo durante la transición.

---

## 5. Plan de Implementación por Fases (Rollout Secuencial)

Los tres pilares están interconectados (Pilar II necesita el grafo de Pilar I; Pilar III alimenta el caché de Pilar II), por lo que la implementación paralela sin secuencia aumenta el riesgo de integración. Se establece el siguiente orden de prioridad:

### Fase 1 — Estabilidad Inmediata (P0): Sin cambios de schema

Estas tareas tienen ROI directo e inmediato sin tocar el schema de la base de datos:

| Tarea | Archivo(s) | Gap resuelto |
|---|---|---|
| Migrar `MemorySummarizer` y `EvolutionDetector` a Gemini | `consolidation_worker.py`, `memory_summarizer.py` | Gap 8 — Causa raíz del 413 |
| Implementar Time Decay (Two-Stage Retrieval) en `hybrid_search.py` | `hybrid_search.py` | Gap 3 — Time Decay no implementado |
| Refactorizar tools de RAG para filtrar por `context_type` | `chat/tools.py`, `tcc/tools.py` | Gap 11 — Contaminación de tipos |
| Implementar lógica hit/miss en `EmbeddingService` | `embeddings.py`, `migration.py` | Gap 1 y 12 — Caché inoperativa |
| Eliminar `session_processor.py` (código muerto) | `session_processor.py` | Gap 4 — Confusión de pipeline |
| Popular `source_skill` en `IngestionPipeline` | `ingestion_pipeline.py` | Gap 10 — Filtro inutilizable |

### Fase 2 — Estructuración y RAG Avanzado (P1): Refactors sin schema change

| Tarea | Archivo(s) | Gap resuelto |
|---|---|---|
| Exponer RAG en `GraphStateV2` + nodo `context_retriever` | `graph.py`, `graph_builder.py` | Gap 2 — RAG invisible al orquestador |
| Migrar `knowledge_base_manager` a ingesta atómica de facts | `knowledge_base.py`, `ingestion_pipeline.py` | Gap 7 — JSON blob chunkeado |
| Corregir fallback frágil de bóveda | `knowledge_base.py` | Gap 5 — Bóveda incompleta silenciosa |
| Implementar Reranker basado en Gemini API | nuevo: `memory/reranker.py` | — |
| Ampliar Redis Cache para la Nota Evolutiva | `consolidation_worker.py`, `memory_summarizer.py` | — |

### Fase 3 — El Grafo y la Ontología (P2): Requiere ADR y migración de schema

| Tarea | Archivo(s) | Requisito previo |
|---|---|---|
| Redactar y aprobar ADR para `parent_id` y `memory_edges` | `adr/` | Fases 1 y 2 completas |
| Añadir `parent_id` a tabla `memories` + índice | `schema.sql`, `migration.py` | ADR aprobado |
| Crear tabla `memory_edges` con índices | `schema.sql`, `migration.py` | ADR aprobado |
| Script de migración one-shot para datos existentes | `scripts/migrate_memory_hierarchy.py` | Schema actualizado |
| Corregir namespaces `user` → `user_{chat_id}` | `ingestion_pipeline.py`, script | Schema actualizado |
| Implementar pipeline de ingesta jerárquica (Gemini Flash) | `ingestion_pipeline.py`, nuevo: `semantic_chunker.py` | Fase 2 completa |
| Implementar Graph-RAG con queries multi-salto (máx 2 saltos) | `hybrid_search.py`, nuevo: `graph_search.py` | `memory_edges` disponible |

---

*Documento actualizado el 26 de Mayo de 2026 con auditoría técnica completa del codebase v0.8.4. Todos los gaps identificados tienen soluciones explícitas y están asignados a una fase de implementación concreta.*
