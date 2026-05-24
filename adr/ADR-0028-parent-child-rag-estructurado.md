# ADR-0028 - Arquitectura Parent-Child RAG y Recuperación Semántica por Umbral

- **Fecha:** 2026-05-22
- **Estado:** Aceptado

## Contexto

El sistema de memoria actual de AEGEN utiliza un RAG (Retrieval-Augmented Generation) estático y un pipeline de ingesta de fuerza bruta (`RecursiveChunker`) que divide los documentos clínicos y transcripciones de forma lineal a 400 tokens con overlap de 80. Esto genera fragmentos de texto crudo y ruidoso en la base de datos vectorial de SQLite.

Al recuperar información para la herramienta de TCC (`cbt_therapeutic_guidance_tool`), el sistema consulta de manera estática los 5 fragmentos más parecidos semánticamente. Cuando la conversación progresa o se ingesta información densa, este flujo causa dos problemas graves:
1. **Ineficacia de Contexto y Ruido Cognitivo:** El LLM recibe fragmentos incompletos, ideas cortadas a la mitad y "ruido" de formato o transcripciones (ej. introducciones, muletillas, avisos publicitarios de YouTube), degradando la calidad clínica de la respuesta de MAGI.
2. **Colapso de Límite de Tokens (413 Rate Limit):** En motores ultra-rápidos de baja latencia como Groq (`gpt-oss-120b`), el límite estricto de 8,000 Tokens Por Minuto (TPM) es superado regularmente por el prompt al inyectarle miles de tokens del RAG y de la base de conocimiento estructurada de forma fija, lo que deja al bot enmudececido o forzado a dar respuestas quemadas ("ruido de mercado").

Adicionalmente, se planifica a futuro integrar un agente de YouTube que ingeste transcripciones completas de canales. Un enfoque de RAG crudo y lineal colapsará de inmediato ante payloads masivos, requiriendo un diseño altamente eficiente e inteligente de inyección de contexto.

## Decisión

Se adopta la arquitectura de **Parent-Child RAG (Padre-Hijo)** y **Recuperación Semántica Adaptativa** como el estándar de almacenamiento y consumo de conocimiento en AEGEN.

### 1. Re-estructuración del Esquema Relacional de Base de Datos
Se modifica la tabla `memories` en `src/memory/schema.sql` para soportar de manera retrocompatible la auto-referencia Padre-Hijo:
- Se añade la columna `parent_id INTEGER REFERENCES memories(id) ON DELETE CASCADE` con su índice correspondiente para consultas óptimas.
- **Chunks Padres (Contexto Coherente):** Se guardan en la tabla `memories` con `parent_id IS NULL` y `memory_type = 'document_parent'`. Representan fragmentos de contexto extendidos (ej. 1,000 a 1,200 tokens) que conservan la idea completa del libro o la transcripción ya limpia. Estos chunks **no** se vectorizan.
- **Chunks Hijos (Embeddings de Alta Resolución):** Se extraen del Chunk Padre y se guardan en `memories` con `parent_id` apuntando a su registro padre y `memory_type = 'document'`. Estos chunks son pequeños (ej. 150-200 tokens), tienen alta densidad semántica y **sí** se vectorizan en `memory_vectors` a través de `vector_memory_map`.

### 2. Pipeline de Ingestión Semántica (`IngestionPipeline`)
El pipeline procesa los textos mediante una lógica de dos capas:
1. Divide el texto fuente en capítulos o bloques grandes (Padres).
2. De cada bloque, extrae sub-fragmentos precisos (Hijos).
3. Inserta ambos en la base de datos vinculando la relación y vectorizando únicamente al Hijo.

### 3. Recuperación Inteligente (RAG por Umbral y Reranking)
Se rediseña la consulta vectorial en `VectorMemoryManager` para actuar en dos etapas:
1. **Recuperación Semántica de Hijos:** Se buscan los vectores más similares al mensaje del usuario en `memory_vectors`.
2. **Filtro de Umbral (Score Gating):** Se añade un umbral estricto de similitud (ej. `score >= 0.70`). Si los fragmentos recuperados están por debajo del umbral (ej. saludos o pláticas cotidianas del usuario), se descartan inmediatamente, resultando en **0 tokens inyectados de RAG** y maximizando la velocidad y el ahorro de recursos.
3. **Resolución de Contexto Padre:** Para los fragmentos que pasan el filtro, el sistema realiza un `JOIN` rápido para extraer su `parent_id`. Al LLM se le inyecta el contenido del **Chunk Padre** (idea completa y coherente) en lugar de la frase atómica y cortada del Hijo.

## Consecuencias

### Positivas
- **Máxima Calidad Cognitiva:** MAGI recibe ideas completas, estructuradas y contextuales de los libros y transcripts en vez de fragmentos incoherentes partidos a la mitad.
- **Eficiencia Extrema de Tokens:** Al no inyectar fragmentos irrelevantes en mensajes casuales (gracias al umbral) y limitar el RAG a fragmentos de alta fidelidad, la ventana de contexto de Groq se mantiene limpia, previniendo el 100% de los errores 413 de chat.
- **Escalabilidad para YouTube:** Habilita que el futuro agente de YouTube ingeste transcripciones masivas de forma limpia y destilada, sin peligro de degradar el rendimiento o la calidad de MAGI.

### Negativas / Riesgos
- **Complejidad en la DB:** Requiere una migración segura en SQLite de producción para añadir la columna `parent_id` a la tabla `memories` sin perder datos ni interrumpir el servicio.
- **Ajuste de Umbrales:** Si el umbral de similitud es demasiado alto (ej. `0.85`), el sistema podría omitir información relevante de libros. Si es demasiado bajo, volvería a inyectar ruido. Se establece un valor inicial de `0.70` sujeto a monitoreo y calibración.
