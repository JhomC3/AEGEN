# Plan de Acción: AEGEN/MAGI (Febrero 2026) - EN PROGRESO 🔄

Este documento resume el estado actual del proyecto AEGEN, los logros recientes y la hoja de ruta para la evolución de la arquitectura, priorizando la memoria local y la eficiencia del sistema.

---

## 🚀 Fase F: Evolución de Memoria (Local-First) 🔄
Estamos migrando la persistencia de largo plazo de **Google File API (Cloud)** a una arquitectura híbrida local optimizada para reducir latencia y mejorar la precisión.

- **F.20 - Infraestructura SQLite:** Implementación de base de datos local con soporte `sqlite-vec` y `FTS5`.
- **F.21 - Pipeline de Ingestión:** Chunking recursivo y deduplicación por hash para optimizar tokens.
- **F.22 - Búsqueda Híbrida:** Implementación de Ranking RRF (Vectorial + Keywords).
- **F.23 - Hooks de Sesión:** Automatización del paso Buffer (Redis) -> Long Term (SQLite).

> Ver detalles en: `docs/refactors/memory_evolution/`

---

## 🔍 Logros Previos (COMPLETADOS ✅)

## 🔍 Análisis de Errores Críticos (RESUELTOS)

### 1. Enrutamiento Incoherente ✅
- **Solución:** Implementación de contexto enriquecido (últimos 5 mensajes) y reglas de continuidad en el prompt.

### 2. Error de Consolidación (JSONDecodeError) ✅
- **Solución:** Extractor robusto basado en regex para limpiar bloques Markdown.

### 3. Timeout de Google File Search ✅
- **Solución:** Implementación de Exponential Backoff para activación de archivos y auditoría de búsqueda global.

---

## 🛠️ Mitigación Técnica (Implementada)

### FASE A: Enrutamiento con Memoria y Afinidad ✅
- **A.1 - Enriquecer Contexto:** Realizado en `routing_utils.py`.
- **A.2 - Formateo de Diálogo:** Realizado en `routing_analyzer.py`.
- **A.3 - Refuerzo de Reglas:** Realizado en `routing_prompts.py`.
- **A.4 - Lógica de Stickiness:** Realizado en `enhanced_router.py`.

### FASE B: Robustez y Auditoría RAG ✅
- **B.5 - Extracción JSON Robusta:** Realizado en `consolidation_worker.py`.
- **B.6 - Exponential Backoff:** Realizado en `google_file_search.py`.
- **B.7 - Conocimiento Global (Knowledge):** Realizado en `google_file_search.py`.

### FASE C: Localización y Consistencia ✅
- **C.8 - Extracción de Language Code:** Realizado en `webhooks.py`.
- **C.9 - Estructura de Perfil:** Realizado en `profile_manager.py`.
- **C.10 - Inyección de Jerga y Zona Horaria:** Realizado en `prompt_builder.py`.

### FASE D: Memoria Híbrida y Precisión Clínica ✅
- **D.11 - Conectar Eslabón Roto:** Conexión `webhooks.py` -> `LongTermMemory` para buffering garantizado.
- **D.12 - Extractor de Hechos (FactExtractor):** Extracción estructurada de entidades, datos médicos y preferencias con precisión clínica.
- **D.13 - Bóveda de Conocimiento (KnowledgeBase):** Almacenamiento dual (Redis working copy + Google Cloud RAG).
- **D.14 - Extracción Incremental:** Disparo de extracción cada 5 mensajes para mantener frescura de datos.
- **D.15 - Inyección en Specialists:** Contexto de hechos confirmados inyectado en el system prompt de MAGI y TCC.

### FASE E: Identidad Estructural y Blindaje de Prompts ✅
- **E.16 - Identidad desde Plataforma:** Captura de `first_name` en Telegram e inicialización no destructiva del perfil.
- **E.17 - Sincronización Knowledge -> Profile:** El nombre aprendido en conversación actualiza automáticamente el perfil del usuario.
- **E.18 - Escapado de Prompts:** Blindaje contra crasheos de LangChain mediante escapado de llaves `{}` en el builder central.
- **E.19 - Robustez RAG:** Sanitización estricta de nombres de archivos para compatibilidad con Google File API.

---

## 🗺️ Roadmap Actualizado: Fase 4 (Skill Ecosystem)

### 0. Evitar urgentemente que el asistente nunca alucine

### 1. Observabilidad Profunda (PRÓXIMO PASO) 🔄
- Integración con **LangSmith** para trazabilidad completa.

### 2. Ecosistema de Micro-Especialistas (Skills)
- Habilidades atómicas: **Google Search, Calendar, Archivos**.

### 3. Skill Creator Tool
- Herramienta automatizada para generar nuevos especialistas.

### 4. Gobernanza Automática
- Validación forzada de `AGENTS.md`.

---

**Estado del Sistema:** `make status` | **Guía Técnica:** `DEVELOPMENT.md`
