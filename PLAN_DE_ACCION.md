# Plan de Acción: AEGEN/MAGI (Enero 2026)

Este documento resume el estado actual del proyecto AEGEN, los logros recientes y el camino hacia la Fase 4, integrando mitigaciones técnicas y mejoras de experiencia de usuario.

---

## 🔍 Análisis de Errores Críticos

### 1. Enrutamiento Incoherente
- **Problema:** El `RoutingAnalyzer` actual solo envía al LLM la longitud del historial y el nombre del especialista anterior, omitiendo el contenido de los mensajes. Esto provoca que el router pierda el contexto en hilos terapéuticos activos (ej: preguntas sobre un ejercicio de TCC) y cambie erróneamente a `chat_specialist`.

### 2. Error de Consolidación (JSONDecodeError)
- **Problema:** El LLM devuelve JSON envuelto en bloques de Markdown (```json ... ```) o con texto explicativo, lo que rompe el `json.loads()` directo en el sistema.

### 3. Timeout de Google File Search
- **Problema:** Los archivos subidos a la API de Google tardan en ocasiones más de los 90 segundos configurados en pasar a estado `ACTIVE`, causando fallos en el RAG. El sistema parece no estar consultando el conocimiento global (`knowledge`) como debería.

---

## 🛠️ Plan de Mitigación Técnica y Refinamiento (Evaluación de Alternativas)

### Fase A: Enrutamiento con Memoria y Afinidad

#### 1. Enriquecer el Contexto (Extracción de Mensajes)
*   **Alt 1 (Historial Completo):** Enviar todos los mensajes del buffer al Router.
    *   *Pros:* Contexto total. *Contras:* Muy ineficiente en tokens y latencia.
*   **Alt 2 (Ventana Deslizante - 3-5 mensajes):** Extraer los últimos mensajes para contexto inmediato.
*   **Alt 3 (RAG de Historial):** Búsqueda semántica de mensajes pasados.
    *   *Pros:* Alta precisión temática. *Contras:* Latencia inaceptable para enrutamiento.
*   **🏆 ELEGIDA: Alt 2.**
    *   *Justificación:* Es el balance ideal entre contexto y eficiencia. Captura la relación pregunta-respuesta inmediata que el router necesita para no romper hilos.

#### 2. Formateo para el Router
*   **Alt 1 (JSON crudo):** Enviar historial como estructura de datos.
    *   *Contras:* Los modelos consumen más razonamiento parseando que analizando.
*   **Alt 2 (Diálogo Natural):** Formato `Usuario: [texto] | Asistente: [texto]`.
*   **Alt 3 (Resumen del Contexto):** Usar un modelo pequeño para resumir el hilo antes del Router.
*   **🏆 ELEGIDA: Alt 2.**
    *   *Justificación:* Los LLM están optimizados para entender diálogos. Reduce la fricción cognitiva y mejora la precisión del enrutamiento.

#### 3. Reglas de Continuidad y Afinidad (Stickiness)
*   **Alt 1 (System Prompt):** Solo instrucciones en lenguaje natural.
*   **Alt 2 (Hard-coding):** Reglas rígidas en Python para forzar continuidad.
    *   *Contras:* Demasiado inflexible, rompe la "inteligencia" del router.
*   **Alt 3 (Inercia con Scoring y Refuerzo):** Inyectar el especialista previo y dar instrucciones de "Inercia".
*   **🏆 ELEGIDA: Alt 3.**
    *   *Justificación:* Permite al Router ser inteligente pero con una fuerte preferencia por la continuidad si el usuario sigue el hilo del especialista anterior.

---

## 📋 Plan de Implementación Detallado

### FASE A: Enrutamiento con Memoria y Afinidad

| Paso | Archivo | Función/Sección | Cambio Específico |
|------|---------|-----------------|-------------------|
| **A.1** | `src/agents/orchestrator/routing/routing_utils.py` | `extract_context_from_state()` | Extraer últimos 5 mensajes de `state["conversation_history"]` y añadir key `recent_messages_content` al dict retornado. |
| **A.2** | `src/agents/orchestrator/routing/routing_analyzer.py` | `_format_context_for_llm()` | Si existe `context["recent_messages_content"]`, formatear como diálogo: `"Usuario: {msg}\nAsistente: {msg}"` y añadir al string de contexto. |
| **A.3** | `src/agents/orchestrator/routing/routing_prompts.py` | `build_routing_prompt()` | Añadir sección **REGLA DE CONTINUIDAD** al system prompt: "Si el usuario responde a una pregunta o ejercicio del especialista previo, MANTÉN ese especialista salvo cambio drástico de tema." |
| **A.4** | `src/agents/orchestrator/routing/enhanced_router.py` | `_apply_routing_decision()` | Implementar lógica de **Stickiness**: Si `decision.target_specialist == state["payload"].get("last_specialist")` Y confianza está entre 0.5-0.7, **boost** a 0.75 para crear inercia. |

---

### FASE B: Robustez y Auditoría RAG

| Paso | Archivo | Función/Sección | Cambio Específico |
|------|---------|-----------------|-------------------|
| **B.5** | `src/memory/consolidation_worker.py` | Nuevo helper: `extract_json_from_response()` | Crear función con regex `r'\{[\s\S]*\}'` para extraer JSON limpio. Llamar antes de `json.loads()`. |
| **B.6** | `src/tools/google_file_search.py` | `_wait_for_active()` | Reemplazar loop fijo con **exponential backoff**: 2s, 4s, 8s, 16s, 32s, 60s. |
| **B.7** | `src/tools/google_file_search.py` | `get_relevant_files()` | Asegurar inclusión de archivos con prefijo `knowledge/` o globales para consulta general. |

---

### FASE C: Localización y Consistencia Multi-plataforma

| Paso | Archivo | Función/Sección | Cambio Específico |
|------|---------|-----------------|-------------------|
| **C.8** | `src/api/routers/webhooks.py` | `telegram_webhook()` | Extraer `language_code` del usuario y pasarlo al estado del grafo. |
| **C.9** | `src/core/profile_manager.py` | `_get_default_profile()` | Añadir estructura `localization` al perfil del usuario. |
| **C.10** | `src/personality/prompt_builder.py` | `build()` | Inyectar reglas de jerga y zona horaria basadas en la localización detectada. |

---

## 🗺️ Roadmap: Fase 4 (Skill Ecosystem)

### 1. Observabilidad Profunda
- Integración con **LangSmith** para trazabilidad completa.

### 2. Ecosistema de Micro-Especialistas (Skills)
- Habilidades atómicas: **Google Search, Calendar, Archivos**.

### 3. Skill Creator Tool
- Herramienta automatizada para generar nuevos especialistas.

### 4. Gobernanza Automática
- Validación forzada de `AGENTS.md`.

---

**Estado del Sistema:** `make status` | **Guía Técnica:** `DEVELOPMENT.md`
