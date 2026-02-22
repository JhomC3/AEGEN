# ADR-0026 - Evolución del Schema de Memoria para Hitos y Metas (State Management)

- **Fecha:** 2026-02-21
- **Estado:** Propuesto

## Contexto

Actualmente, AEGEN posee una memoria basada en eventos y hechos ("RAG pasivo"). La base de datos (`schema.sql`) almacena transcripciones de chat, hechos extraídos (`fact`, `preference`) y documentos embebidos. Sin embargo, el asistente no tiene la capacidad de realizar un seguimiento estructurado del "estado de vida" del usuario.
Por ejemplo, si el usuario menciona que "fue a entrenar a pesar de la apatía", el sistema lo guarda como un hecho aislado, pero no lo reconoce como un "Hito" (Milestone) ligado a una meta más amplia (Salud/Fitness).
Para que AEGEN deje de ser un chatbot reactivo y se convierta en un Sistema de Soporte Vital, el agente necesita entender el propósito detrás de las acciones, guardar hitos temporales y usar esta información para generar "hilos conductores" en futuras conversaciones.

## Decisión

1. **Ampliar el esquema de base de datos (`schema.sql`):**
   - Introducir la tabla `user_goals` para rastrear objetivos a largo plazo del usuario (ej. Entrenar regularmente, Ahorrar, Controlar la ansiedad).
   - Introducir la tabla `user_milestones` (Hitos) que registrará eventos temporales específicos ligados a una acción, un estado y una emoción (ej. `action: Gimnasio`, `status: Completado`, `emotion: Apatía`).
   - Estas tablas se relacionarán con el `chat_id` para garantizar el aislamiento por usuario.

2. **Implementar un Extractor de Hitos en Background:**
   - Crear un sub-agente (worker) o un nodo en el pipeline de consolidación (`src/memory/services/`) que, al finalizar un ciclo conversacional, analice si el usuario ha reportado algún avance, retroceso o evento significativo.
   - De ser así, se insertará un registro estructurado en la base de datos de hitos.

3. **Inyectar el Estado (State Management) en el Contexto:**
   - Modificar `src/personality/prompt_builder.py` para cargar los hitos recientes y las metas activas del usuario, proporcionando a MAGI un "contexto de propósito" para que pueda preguntar y hacer seguimiento en las conversaciones (ej. "¿Cómo siguió esa apatía de ayer?").

## Consecuencias

### Positivas
- Permite que el asistente inicie hilos conversacionales con un propósito claro y sostenido a lo largo del tiempo.
- Reduce la percepción de que el asistente "solo responde" (Q&A aislado).
- Posibilita el desarrollo futuro de skills específicos basados en seguimiento (finanzas, fitness, nutrición).

### Negativas / Riesgos
- **Complejidad del Schema:** Aumenta la complejidad relacional de `schema.sql` y de los procesos de migración (`migration.py`).
- **Precisión de Extracción:** El LLM encargado de extraer hitos en background podría generar falsos positivos (crear metas que el usuario no deseaba realmente establecer).
- Requiere ajustes en el pipeline asíncrono de consolidación para no ralentizar la respuesta en tiempo real al usuario.
