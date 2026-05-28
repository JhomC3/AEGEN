# ADR-0029 - Migración de Modelos de Consolidación de Groq a Gemini

- **Fecha:** 2026-05-26
- **Estado:** Aceptado
- **Autor:** Lead Architect & MAGI AI
- **ADR Relacionado:** ADR-0027 (Inteligencia Asimétrica), ADR-0028 (Parent-Child RAG)

## Contexto

El sistema de consolidación en background (`ConsolidationManager`) y el extractor incremental (`IncrementalExtractor`) utilizan actualmente el modelo global de Groq (`openai/gpt-oss-120b`) para dos tareas pesadas:

1. **`MemorySummarizer`** (`src/memory/services/memory_summarizer.py:64`): Genera el resumen de largo plazo de la sesión de conversación.
2. **`EvolutionDetector`** (`src/memory/consolidation_worker.py:18`): Analiza cambios en valores, estilo y metas del usuario.

Groq impone un Rate Limit estricto de **8,000 Tokens Por Minuto (TPM)**. En conversaciones activas y largas, los procesos de background compiten con las respuestas conversacionales en tiempo real por la misma cuota de TPM. Esto provoca errores `413 Request too large` que enmudecen al bot. Este es el bug de infraestructura que ADR-0028 atribuyó incorrectamente solo al chunking — el error `413` no es causado por el tamaño de un request individual del chunker, sino por la acumulación de consumo TPM concurrente.

La arquitectura de Inteligencia Asimétrica (ADR-0027) establece que Groq debe ser el motor de **respuestas conversacionales en tiempo real** exclusivamente, dado su ventaja de baja latencia. Los procesos de background no requieren baja latencia — requieren calidad analítica y contexto largo. Gemini Flash es superior en ambas dimensiones para estas tareas.

## Decisión

Se migran `MemorySummarizer` y `EvolutionDetector` del modelo global Groq a **Gemini Flash** (`gemini-2.5-flash` o equivalente disponible), accesible vía `get_rag_llm()` ya definido en `src/core/engine.py`.

### Cambios concretos

1. **`src/memory/services/memory_summarizer.py`**: Reemplazar la instancia de `llm` global por `get_rag_llm()` en la construcción de la cadena de sumarización.
2. **`src/memory/consolidation_worker.py`**: Reemplazar la instancia de `llm` global en el bloque de `EvolutionDetector` por `get_rag_llm()`.
3. **Partición de cuota TPM**: Groq queda reservado al 100% para el path crítico: Router → Chat → TCC → respuesta. Gemini absorbe todo el background cognitivo.
4. **Sin cambio de interfaz pública**: `ConsolidationManager`, `LongTermMemoryManager` y todos sus callers mantienen sus firmas actuales. El cambio es interno a los workers.

## Consecuencias

### Positivas
- **Eliminación de la causa raíz del error `413`**: Al separar completamente las cuotas, el path conversacional nunca vuelve a competir con los workers de background.
- **Mayor calidad de consolidación**: Gemini Flash maneja ventanas de contexto más grandes, permitiendo sumarizaciones más completas en sesiones largas.
- **Alineación con ADR-0027**: La partición de modelos se vuelve coherente — Groq para latencia, Gemini para análisis y contexto.

### Negativas / Riesgos
- **Latencia de consolidación**: Gemini puede ser más lento que Groq para inferencia. Es aceptable porque la consolidación ocurre en background, no en el path crítico.
- **Dependencia adicional de cuota Gemini**: Si la cuota de Gemini se agota (menos probable dado su límite mayor), los workers de consolidación fallan silenciosamente. El sistema ya tiene mecanismo de Redis Lock para no reintentar infinitamente.
- **Costo Gemini API**: La consolidación ocurre cada 10 mensajes o 30 minutos. El costo incremental es despreciable comparado con la estabilidad ganada.
